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

DATA_DIR <- file.path("data")
INTRADAY_DIR <- file.path(DATA_DIR, "intraday")
dir.create(INTRADAY_DIR, showWarnings = FALSE)
LOG_FILE <- file.path(DATA_DIR, "_scrape_log.csv")

scrape_brvm <- function() {
  url <- "https://www.brvm.org/fr/cours-actions/liste"

  resp <- GET(url, user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"), timeout(30))
  if (status_code(resp) != 200) {
    stop(glue("HTTP {status_code(resp)}"))
  }

  page <- content(resp, "text", encoding = "UTF-8") %>% read_html()
  tables <- page %>% html_elements("table")
  stock_table <- tables[[4]]
  rows <- stock_table %>% html_elements("tr")

  scrape_time <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  scrape_date <- Sys.Date()

  df_list <- list()
  for (i in seq_len(length(rows))[-1]) {
    cells <- rows[i] %>% html_elements("td") %>% html_text2()
    if (length(cells) < 7) next

    df_list[[length(df_list) + 1]] <- data.frame(
      Ticker = cells[1],
      Nom = cells[2],
      Volume = as.numeric(gsub(" ", "", cells[3])),
      Cours_Veille = as.numeric(gsub(" ", "", cells[4])),
      Cours_Ouverture = as.numeric(gsub(" ", "", cells[5])),
      Cours_Cloture = as.numeric(gsub(" ", "", cells[6])),
      Variation = as.numeric(gsub(",", ".", gsub(" ", "", cells[7]))),
      Date = as.character(scrape_date),
      Timestamp = scrape_time,
      stringsAsFactors = FALSE
    )
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
})
