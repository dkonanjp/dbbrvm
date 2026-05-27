# =====================================================================
# INIT BRVM DATABASE (CSV)
# Initialisation de la base CSV depuis le repo GitHub
# Usage: Rscript init_brvm_db.R
# =====================================================================

suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(glue)
})

DATA_DIR <- file.path("data")
dir.create(DATA_DIR, showWarnings = FALSE)

TICKERS <- c(
  "NTLC", "PALC", "SPHC", "SICC", "STBC", "SOGC", "SLBC", "SCRC", "UNLC",
  "BNBC", "CFAC", "LNBB", "NEIC", "ABJC", "PRSC", "UNXC",
  "SMBC", "TTLC", "TTLS", "SHEC",
  "SDSC", "SEMC", "SIVC", "FTSC", "STAC", "CABC",
  "BOAB", "BOABF", "BOAC", "BOAM", "BOAN", "BOAS",
  "BICB", "BICC", "CBIBF", "ECOC", "ETIT", "NSBC", "ORGT", "SAFC", "SGBC", "SIBC",
  "CIEC", "SDCC",
  "ONTBF", "ORAC", "SNTS"
)

BASE_URL <- "https://raw.githubusercontent.com/Fredysessie/brvm-data-public/main/data"

cat("=== Initialisation de la base BRVM CSV ===\n\n")

total_rows <- 0
for (ticker in TICKERS) {
  url <- glue("{BASE_URL}/{ticker}/{ticker}.daily.csv")
  dest <- file.path(DATA_DIR, glue("{ticker}.csv"))
  
  cat(sprintf("[%s] Téléchargement... ", ticker))
  
  df <- tryCatch({
    read_csv(url, show_col_types = FALSE) %>%
      mutate(
        Date = as.Date(Date),
        Ticker = ticker,
        source = "github",
        updated_at = Sys.time()
      ) %>%
      select(Date, Open, High, Low, Close, Volume, Ticker, source, updated_at) %>%
      arrange(Date)
  }, error = function(e) {
    cat(sprintf("ERREUR: %s\n", e$message))
    return(NULL)
  })
  
  if (is.null(df) || nrow(df) == 0) {
    cat("⚠️  aucun fichier\n")
    next
  }
  
  write_csv(df, dest)
  rows <- nrow(df)
  total_rows <- total_rows + rows
  
  cat(sprintf("✅ %d lignes (dernière: %s)\n", rows, format(max(df$Date), "%Y-%m-%d")))
}

cat(sprintf("\n=== Terminé: %d tickers, %d lignes total ===\n", length(TICKERS), total_rows))
