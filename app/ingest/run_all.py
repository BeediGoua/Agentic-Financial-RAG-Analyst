import argparse
import logging
import sys

from app.ingest.run_reports import main as run_brvm_reports
from app.ingest.sika_source import run_ingestion as run_sika
from app.ingest.macro_source import run_macro_ingestion as run_macro

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Orchestrateur global d'ingestion (Phase 1)")
    
    parser.add_argument("--only-brvm", action="store_true", help="Ne lancer que l'ingestion des PDFs BRVM")
    parser.add_argument("--only-sika", action="store_true", help="Ne lancer que l'ingestion Sika (cours de bourse)")
    parser.add_argument("--only-macro", action="store_true", help="Ne lancer que l'ingestion Macro")
    parser.add_argument("--probe", action="store_true", help="Mode test rapide (Sika)")
    
    args, unknown = parser.parse_known_args()
    
    run_all = not (args.only_brvm or args.only_sika or args.only_macro)
    
    if run_all or args.only_macro:
        logging.info("Lancement Ingestion MACRO")
        try:
            run_macro()
        except Exception as e:
            logging.error(f"Echec Ingestion Macro: {e}")
            
    if run_all or args.only_sika:
        logging.info("Lancement Ingestion SIKA")
        try:
            run_sika(probe=args.probe, force=False)
        except Exception as e:
            logging.error(f"Echec Ingestion Sika: {e}")
            
    if run_all or args.only_brvm:
        logging.info("Lancement Ingestion BRVM PDFs")
        # Restore sys.argv with only the unknown args so run_reports parses them correctly
        original_argv = sys.argv
        sys.argv = [sys.argv[0]] + unknown
        try:
            run_brvm_reports()
        except Exception as e:
            logging.error(f"Echec Ingestion BRVM PDFs: {e}")
        finally:
            sys.argv = original_argv
            
    logging.info("Fin de l'orchestration globale")

if __name__ == "__main__":
    main()
