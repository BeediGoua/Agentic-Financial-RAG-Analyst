# SOUS-ÉTAPE — ORCHESTRATION GLOBALE DU PIPELINE (PHASE 1 → PHASE 3)

## Objectif

Avant de continuer vers le chunking et le RAG, nous avons ajouté une couche d’orchestration globale du pipeline.

Le but est de pouvoir :

- lancer chaque phase individuellement ;
- lancer plusieurs phases automatiquement ;
- suivre l’avancement du pipeline ;
- centraliser les logs ;
- produire un rapport global d’exécution ;
- détecter les erreurs avant les étapes suivantes.

Cette sous-étape transforme le projet en véritable pipeline data modulaire.

---

# Pourquoi cette sous-étape est importante

Sans orchestration globale :

- chaque étape doit être lancée manuellement ;
- les erreurs deviennent difficiles à suivre ;
- les logs sont dispersés ;
- les dépendances entre phases sont fragiles ;
- le pipeline devient difficile à maintenir.

Avec orchestration :

text id="8m6b5s" Ingestion ↓ Extraction ↓ Audit extraction ↓ Processing ↓ Rapport global

Le système devient :

- reproductible ;
- automatisable ;
- plus proche d’un pipeline production réel.

---

# Ce que cette sous-étape apporte

## Avant

Exécution manuelle :

bash id="x92hyk" python -m app.ingest.run_all python -m app.extraction.run_extraction python -m app.extraction.extraction_audit python -m app.processing.run_processing

## Après

Pipeline orchestré :

bash id="c5cr1v" python -m app.pipeline.run_data_pipeline

---

# Structure ajoutée

text id="jlwm3o" app/ pipeline/ __init__.py run_data_pipeline.py

---

# Architecture globale

text id="a8vxru" PHASE 1 — Ingestion ↓ PHASE 2 — Extraction ↓ PHASE 2.5 — Extraction Audit ↓ PHASE 3 — Processing ↓ Rapport pipeline global

---

# Composant principal

## DataPipelineRunner

Fichier :

text id="k5dd78" app/pipeline/run_data_pipeline.py

Rôle :

- orchestrer les phases ;
- lancer les sous-commandes ;
- gérer les erreurs ;
- mesurer les durées ;
- centraliser les logs ;
- produire un rapport global.

---

# Fonctionnement interne

Le pipeline utilise :

text id="40jye1" subprocess.run()

pour lancer les différents modules Python :

text id="mlzqgu" app.ingest.run_all app.extraction.run_extraction app.extraction.extraction_audit app.processing.run_processing

Chaque phase reste donc indépendante, mais peut être orchestrée automatiquement.

---

# Barre de progression

Le pipeline utilise :

text id="33f55s" tqdm

pour afficher une progression globale :

text id="8r8bl4" Running ingestion Running extraction Running audit Running processing

Cela permet :

- de suivre l’avancement ;
- de voir quelle phase prend du temps ;
- de détecter les blocages.

---

# Rapports générés

Sortie :

text id="j7lnqv" data/pipeline_runs/

Exemple :

text id="u4dx0p" pipeline_run_20260510_183000.json

---

# Contenu du rapport

Le rapport contient :

- status global ;
- phases exécutées ;
- durée par phase ;
- commandes lancées ;
- stdout ;
- stderr ;
- erreurs éventuelles.

Exemple :

json id="8w7jmt" { "overall_status": "success", "phases": [ { "phase": "phase_1_ingestion", "status": "success", "duration_seconds": 52.1 }, { "phase": "phase_2_extraction", "status": "success", "duration_seconds": 21.7 } ] }

---

# Modes d’utilisation

## Lancer tout le pipeline

bash id="z5j6rw" python -m app.pipeline.run_data_pipeline \ --companies "ORAC" \ --years "2024-2026"

---

## Lancer uniquement ingestion

bash id="q0kivj" python -m app.pipeline.run_data_pipeline \ --stop-after ingestion

---

## Reprendre à partir extraction

bash id="r9fpxv" python -m app.pipeline.run_data_pipeline \ --start-from extraction

---

## Lancer uniquement audit extraction

python -m app.pipeline.run_data_pipeline \ --start-from audit \ --stop-after audit

---