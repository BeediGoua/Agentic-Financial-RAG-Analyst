# BRVM Financial Report Ingestion

Pipeline d'ingestion déterministe pour télécharger les rapports financiers publics BRVM par entreprise et par année.

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

Une entreprise, une année :

```bash
python -m app.ingest.run_reports --companies "CIE CI" --years "2024" --limit 5
```

Plusieurs entreprises, plusieurs années :

```bash
python -m app.ingest.run_reports --companies "CIE CI,SONATEL,ORANGE CI" --years "2023,2024" --limit 20
```

Toutes les entreprises pour une année :

```bash
python -m app.ingest.run_reports --years "2024" --limit 30
```

## Architecture

- `BRVMSourceAgent` : découvre les rapports BRVM disponibles.
- `QualityAgent` : valide les PDF, calcule les checksums, détecte les doublons.
- `StorageAgent` : télécharge les fichiers, organise le stockage, écrit les manifests.
- `SupervisorAgent` : orchestre le pipeline complet.

À cette étape, aucun LLM n'est nécessaire. Les agents sont des classes Python déterministes.
