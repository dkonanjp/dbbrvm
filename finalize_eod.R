# =====================================================================
# FINALIZE EOD — Calcul OHLCV journalier à partir des snapshots intraday
# Lit data/intraday/{TICKER}.csv → calcule Open/High/Low/Close/Volume
# → Append dans data/{TICKER}.csv avec source="live"
# Nettoie les snapshots du jour
# Usage: Rscript finalize_eod.R
# =====================================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(glue)
})

HISTORICAL_DIR <- file.path("dbhistorical")
INTRADAY_DIR <- file.path("dbintraday")

compute_eod <- function(intraday_csv) {
  df <- read_csv(intraday_csv, show_col_types = FALSE)

  if (nrow(df) == 0) return(NULL)

  ticker <- unique(df$Ticker)
  if (length(ticker) != 1) {
    warning(glue("{intraday_csv}: tickers multiples, ignoré"))
    return(NULL)
  }

  today <- unique(df$Date)
  if (length(today) != 1) {
    warning(glue("{intraday_csv}: dates multiples, ignoré"))
    return(NULL)
  }

  df <- df %>% arrange(Timestamp)

  eod <- data.frame(
    Date = as.Date(today[1]),
    Open = df$Cours_Ouverture[1],
    High = max(df$Cours, na.rm = TRUE),
    Low = min(df$Cours, na.rm = TRUE),
    Close = df$Cours[nrow(df)],
    Volume = df$Volume_Cumule[nrow(df)],
    Ticker = ticker[1],
    source = "live",
    updated_at = Sys.time(),
    stringsAsFactors = FALSE
  )

  return(eod)
}

cat("=== Finalisation EOD BRVM ===\n")
cat(sprintf("Date: %s\n\n", Sys.Date()))

intraday_files <- list.files(INTRADAY_DIR, pattern = "^[A-Z]+\\.csv$", full.names = TRUE)

if (length(intraday_files) == 0) {
  cat("  Aucun snapshot intraday trouvé.\n")
  quit(save = "no", status = 0)
}

success <- 0
for (f in intraday_files) {
  ticker <- gsub("\\.csv$", "", basename(f))
  cat(sprintf("  %-5s → ", ticker))

  eod <- compute_eod(f)
  if (is.null(eod)) {
    cat("pas de données\n")
    next
  }

  daily_file <- file.path(HISTORICAL_DIR, glue("{ticker}.csv"))

  if (file.exists(daily_file)) {
    existing <- read_csv(daily_file, show_col_types = FALSE)
    existing <- existing %>% filter(Date != eod$Date[1])
    existing <- bind_rows(existing, eod) %>% arrange(Date)
  } else {
    existing <- eod
  }

  write_csv(existing, daily_file)

  cat(sprintf("O:%.0f H:%.0f L:%.0f C:%.0f V:%s\n",
              eod$Open, eod$High, eod$Low, eod$Close,
              format(eod$Volume, big.mark = ",")))
  success <- success + 1
}

cat(sprintf("\n  %d tickers finalisés dans %s/\n", success, HISTORICAL_DIR))
