# =====================================================================
# UPDATE BRVM DATABASE — Snapshot 15 min (intraday)
# Scrape brvm.org et append le snapshot dans data/intraday/
# Usage: Rscript update_brvm_db.R
# =====================================================================

suppressPackageStartupMessages({
  library(rvest)
  library(httr)
  library(dplyr)
  library(readr)
  library(glue)
})

HISTORICAL_DIR <- file.path("dbhistorical")
INTRADAY_DIR <- file.path("dbintraday")
LOG_DIR <- file.path("logs")
dir.create(INTRADAY_DIR, showWarnings = FALSE)
dir.create(LOG_DIR, showWarnings = FALSE)
LOG_FILE <- file.path(LOG_DIR, "_scrape_log.csv")

USER_AGENTS <- c(
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0"
)

request_with_retry <- function(url, max_attempts = 3) {
  ua <- sample(USER_AGENTS, 1)
  for (attempt in seq_len(max_attempts)) {
    resp <- tryCatch(
      GET(url, user_agent(ua), timeout(30), add_headers(
        "Accept-Language" = "fr,fr-FR;q=0.9,en;q=0.8",
        "Accept" = "text/html,application/xhtml+xml",
        "Referer" = "https://www.brvm.org/fr/"
      )),
      error = function(e) NULL
    )
    if (!is.null(resp) && status_code(resp) == 200) return(resp)
    if (!is.null(resp) && status_code(resp) == 429) {
      wait <- 2 ^ attempt * 5
      cat(sprintf("  429 Too Many Requests — attente %ds (tentative %d/%d)\n", wait, attempt, max_attempts))
      Sys.sleep(wait)
      next
    }
    if (attempt < max_attempts) {
      cat(sprintf("  Tentative %d/%d échouée, nouvelle tentative...\n", attempt, max_attempts))
      Sys.sleep(5)
    }
  }
  return(NULL)
}

scrape_brvm <- function() {
  url <- "https://www.brvm.org/fr/cours-actions/liste"
  resp <- request_with_retry(url)

  if (is.null(resp)) {
    stop("Échec après plusieurs tentatives")
  }

  page <- content(resp, "text", encoding = "UTF-8") %>% read_html()
  tables <- page %>% html_elements("table")
  if (length(tables) < 4) {
    stop("Tableau 4 introuvable — la structure HTML a peut-être changé")
  }
  stock_table <- tables[[4]]
  rows <- stock_table %>% html_elements("tr")

  scrape_time <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  scrape_date <- Sys.Date()

  df_list <- list()
  for (i in seq_len(length(rows))[-1]) {
    cells <- rows[i] %>% html_elements("td") %>% html_text2()
    if (length(cells) < 7) next

    cours_cloture <- as.numeric(gsub(" ", "", cells[6]))
    if (is.na(cours_cloture) || cours_cloture == 0) next

    df_list[[length(df_list) + 1]] <- data.frame(
      Ticker = cells[1],
      Nom = cells[2],
      Volume = as.numeric(gsub(" ", "", cells[3])),
      Cours_Veille = as.numeric(gsub(" ", "", cells[4])),
      Cours_Ouverture = as.numeric(gsub(" ", "", cells[5])),
      Cours_Cloture = cours_cloture,
      Variation = as.numeric(gsub(",", ".", gsub(" ", "", cells[7]))),
      Date = as.character(scrape_date),
      Timestamp = scrape_time,
      stringsAsFactors = FALSE
    )
  }

  if (length(df_list) == 0) {
    stop("Aucune donnée valide extraite")
  }

  df <- do.call(rbind, df_list)
  attr(df, "scrape_time") <- scrape_time
  return(df)
}

append_intraday <- function(df) {
  for (ticker in unique(df$Ticker)) {
    df_ticker <- df[df$Ticker == ticker, ]
    filepath <- file.path(INTRADAY_DIR, glue("{ticker}.csv"))

    snapshot <- df_ticker %>%
      select(Ticker, Date, Timestamp, Cours_Ouverture, Cours = Cours_Cloture, Volume_Cumule = Volume)

    write_csv(snapshot, filepath, append = file.exists(filepath))
  }
}

log_scrape <- function(success_count, error_count, scrape_time) {
  log_entry <- data.frame(
    timestamp = scrape_time,
    date = Sys.Date(),
    success = success_count,
    errors = error_count,
    total = success_count + error_count,
    stringsAsFactors = FALSE
  )

  if (file.exists(LOG_FILE)) {
    write_csv(log_entry, LOG_FILE, append = TRUE)
  } else {
    write_csv(log_entry, LOG_FILE)
  }
}

cat("=== Snapshot BRVM ===\n")
cat(sprintf("Date: %s\n\n", Sys.Date()))

tryCatch({
  df <- scrape_brvm()
  scrape_time <- attr(df, "scrape_time")

  cat(sprintf("  %d actions récupérées à %s\n\n", nrow(df), scrape_time))

  success <- 0
  for (ticker in unique(df$Ticker)) {
    df_ticker <- df[df$Ticker == ticker, ]
    cat(sprintf("  %-5s → Cours: %8.0f FCFA | Vol: %s\n",
                ticker,
                df_ticker$Cours_Cloture[1],
                format(df_ticker$Volume[1], big.mark = ",")))
    success <- success + 1
  }

  append_intraday(df)

  log_scrape(success, nrow(df) - success, scrape_time)
  cat(sprintf("\n  Snapshot sauvegardé dans %s/\n", INTRADAY_DIR))

}, error = function(e) {
  cat(sprintf("\nERREUR: %s\n", e$message))
  log_scrape(0, 1, format(Sys.time(), "%Y-%m-%d %H:%M:%S"))
  quit(save = "no", status = 1)
})
