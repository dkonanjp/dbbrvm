# =====================================================================
# PROJET PARALLÈLE : Historique BRVM (GitHub) + Scraping temps réel
# =====================================================================

suppressPackageStartupMessages({
  library(rvest)
  library(httr)
  library(dplyr)
  library(lubridate)
  library(readr)
})

cat("=== Initialisation du Laboratoire de Scraping R ===\n\n")

# =====================================================================
# 1. Chargement de l'Historique depuis le repo GitHub
# (https://github.com/Fredysessie/brvm-data-public)
# =====================================================================
charger_historique_github <- function(ticker) {
  cat(sprintf("[GitHub] Téléchargement de l'historique daily pour %s...\n", ticker))
  
  # URL brute (raw) du CSV sur GitHub
  url_csv <- sprintf("https://raw.githubusercontent.com/Fredysessie/brvm-data-public/main/data/%s/%s.daily.csv", ticker, ticker)
  
  historique <- tryCatch({
    # read_csv de readr gère très bien le téléchargement direct
    read_csv(url_csv, show_col_types = FALSE) %>%
      # On s'assure que les dates sont bien formatées
      mutate(Date = as.Date(Date)) %>%
      arrange(Date)
  }, error = function(e) {
    message("Erreur lors du téléchargement de l'historique : ", e$message)
    return(data.frame())
  })
  
  return(historique)
}

# =====================================================================
# 2. Scraping des données journalières / 15 minutes (BRVM Officiel)
# =====================================================================
scraper_brvm_recent <- function(ticker = NULL) {
  url_cible <- "https://www.brvm.org/fr/cours-actions/liste"
  
  cat(sprintf("[Scraping] Récupération des cours BRVM depuis %s...\n", url_cible))
  
  response <- tryCatch({
    GET(url_cible, user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"), timeout(30))
  }, error = function(e) {
    message("Erreur HTTP : ", e$message)
    return(NULL)
  })
  
  if (is.null(response) || status_code(response) != 200) {
    cat("[Scraping] Échec de la récupération de la page\n")
    return(data.frame())
  }
  
  page <- content(response, "text", encoding = "UTF-8") %>% read_html()
  
  # Table 4 = tableau des actions
  stock_table <- page %>% html_elements("table") %>% .[[4]]
  rows <- stock_table %>% html_elements("tr")
  
  df_list <- list()
  for (i in seq_len(length(rows))[-1]) {
    cells <- rows[i] %>% html_elements("td") %>% html_text2()
    if (length(cells) < 7) next
    
    variation <- cells[7] %>% gsub(",", ".", .) %>% gsub(" ", "", .)
    volume <- cells[3] %>% gsub(" ", "", .)
    veille <- cells[4] %>% gsub(" ", "", .)
    ouverture <- cells[5] %>% gsub(" ", "", .)
    cloture <- cells[6] %>% gsub(" ", "", .)
    
    df_list[[length(df_list) + 1]] <- data.frame(
      Ticker = cells[1],
      Nom = cells[2],
      Volume = as.numeric(volume),
      Cours_Veille = as.numeric(veille),
      Cours_Ouverture = as.numeric(ouverture),
      Cours_Cloture = as.numeric(cloture),
      Variation = as.numeric(variation),
      Date = Sys.Date(),
      Timestamp = format(Sys.time(), "%Y-%m-%d %H:%M:%S"),
      stringsAsFactors = FALSE
    )
  }
  
  df <- do.call(rbind, df_list)
  cat(sprintf("[Scraping] ✅ %d actions récupérées à %s\n", nrow(df), format(Sys.time(), "%H:%M:%S")))
  
  if (!is.null(ticker)) {
    df <- df[df$Ticker == ticker, ]
    cat(sprintf("[Scraping] Filtrage pour %s: %d lignes\n", ticker, nrow(df)))
  }
  
  return(df)
}

# =====================================================================
# 3. Pipeline d'Exécution : Combiner les deux sources
# =====================================================================
ticker_cible <- "SNTS"

# A. Récupérer le "socle" historique
historique_complet <- charger_historique_github(ticker_cible)

if(nrow(historique_complet) > 0) {
  cat(sprintf("Succès : %d lignes historiques récupérées.\n", nrow(historique_complet)))
  print(tail(historique_complet)) # Affiche les dates les plus récentes du GitHub
  
  # B. Récupérer les données fraîches (scraping BRVM direct)
  donnees_jour <- scraper_brvm_recent(ticker_cible)
  
  if(nrow(donnees_jour) > 0 && !is.na(donnees_jour$Cours_Cloture[1])) {
    # Ajouter les colonnes Open/High/Low à partir des données BRVM
    # (le scraping temps réel donne Cours_Ouverture comme Open,
    #  on utilise Cours_Cloture comme Close, et on déduit High/Low)
    historique_complet <- bind_rows(
      historique_complet,
      donnees_jour %>% transmute(
        Date = as.Date(.data$Date),
        Open = .data$Cours_Ouverture,
        High = pmax(.data$Cours_Ouverture, .data$Cours_Cloture, .data$Cours_Veille, na.rm = TRUE),
        Low  = pmin(.data$Cours_Ouverture, .data$Cours_Cloture, .data$Cours_Veille, na.rm = TRUE),
        Close = .data$Cours_Cloture,
        Volume = .data$Volume
      )
    ) %>%
      distinct(Date, .keep_all = TRUE) %>%
      arrange(Date)
    
    cat(sprintf("[Pipeline] Fusionné avec le cours BRVM du %s (Clôture: %.0f FCFA)\n",
                donnees_jour$Date[1], donnees_jour$Cours_Cloture[1]))
  } else {
    cat("[Pipeline] Pas de nouvelle donnée temps réel (marché fermé ?)\n")
  }
  
  # Sauvegarde
  fichier_sortie <- paste0("dataset_combine_", ticker_cible, ".csv")
  write_csv(historique_complet, fichier_sortie)
  cat(sprintf("\n[Pipeline] Dataset final prêt et sauvegardé : %s\n", fichier_sortie))
  
} else {
  cat("Impossible de lancer le pipeline, l'historique de base est introuvable.\n")
}
