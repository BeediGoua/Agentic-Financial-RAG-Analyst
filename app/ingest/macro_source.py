"""
Ingestion Macro "No-Silent-Fail".
Ce script est chargé de lire les données EDEN.
S'il échoue, il doit crash bruyamment via une Exception, et ne JAMAIS injecter
de fausses valeurs par défaut comme c'était le cas dans l'ancienne V3.
"""
import pandas as pd
import logging
from pathlib import Path
import os
import sys

from app.core.atomic import atomic_text_writer
from app.core.manifests import create_manifest, write_manifest

def parse_eden_csv_fake_xls(file_path: str, value_column: str) -> pd.DataFrame:
    """
    Parse les faux fichiers XLS d'EDEN qui sont en réalité des CSV Séparés par ';'.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"🚨 FATAL: Fichier Macro manquant: {file_path}. Le modèle risque l'aveuglement.")
        
    logging.info(f"Tentative de parsing du fichier EDEN: {Path(file_path).name}")
    try:
        # Le format EDEN réel a 5 lignes de métadonnées avant le header CSV
        df = pd.read_csv(file_path, sep=";", skiprows=5)
        
        # Nettoyage des colonnes : On garde les infos descriptives et on melt le reste (les dates)
        id_cols = ["CODE", "LIBELLE", "UNITE DE MESURE", "MAGNITUDE", "SOURCE", "TYPE SERIE", "METHODE OBSERVATION"]
        # On s'assure que ces colonnes existent avant de melt
        available_id_cols = [c for c in id_cols if c in df.columns]
        
        melted_df = df.melt(id_vars=available_id_cols, var_name="Date_Raw", value_name=value_column)
        
        # Nettoyage optionnel des lignes vides (EDEN remplit de '-' les trous)
        values = melted_df[value_column].astype("string").str.strip()
        melted_df = melted_df[
            melted_df[value_column].notna() & values.ne("") & values.ne("-")
        ]
        if melted_df.empty:
            raise ValueError(f"No usable observations in EDEN file {file_path}")
        
        return melted_df
    except Exception as e:
         raise RuntimeError(f"🚨 FATAL: Le parsing du fichier Macro EDEN {file_path} a échoué. Corriger la source. Erreur: {e}")

def run_macro_ingestion():
    base_dir = Path(__file__).resolve().parent.parent.parent
    
    # Fichiers sources supposés (A adapter selon le vrai chemin des raw data de l'utilisateur)
    raw_rates_path = base_dir / "data" / "raw" / "eden_rates.xls"
    raw_cpi_path = base_dir / "data" / "raw" / "eden_cpi_monthly_uemoa.xls"
    
    missing = [
        str(path)
        for path in (raw_rates_path, raw_cpi_path)
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(f"Required EDEN macro inputs missing: {missing}")
    bronze_dir = base_dir / "data" / "bronze"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir = base_dir / "data" / "manifests"
    
    # Tenter l'ingestion stricte
    try:
        df_rates = parse_eden_csv_fake_xls(str(raw_rates_path), "taux_directeur")
        out_rates = bronze_dir / "macro_rates.csv"
        with atomic_text_writer(out_rates) as output:
            df_rates.to_csv(output, index=False)
            
        manifest_rates = create_manifest(str(out_rates), str(raw_rates_path), "EDEN_BCEAO", {"type": "rates"})
        write_manifest(manifest_rates, str(manifests_dir))
        logging.info(" Macro Rates ingérés avec succès.")
            
        df_cpi = parse_eden_csv_fake_xls(str(raw_cpi_path), "inflation")
        out_cpi = bronze_dir / "macro_cpi.csv"
        with atomic_text_writer(out_cpi) as output:
            df_cpi.to_csv(output, index=False)
            
        manifest_cpi = create_manifest(str(out_cpi), str(raw_cpi_path), "EDEN_BCEAO", {"type": "cpi"})
        write_manifest(manifest_cpi, str(manifests_dir))
        logging.info(" Macro CPI ingérée avec succès.")
            
    except Exception as e:
        # Exception levée volontairement pour crash le pipeline et empêcher les "Default Values"
        logging.error(str(e))
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_macro_ingestion()
