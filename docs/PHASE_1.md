# Phase 1 : Collecte et Stockage des Données

## Objectif General

Construire une **pipeline d'ingestion fiable** pour collecter, valider et stocker les rapports financiers publics de la **BRVM (Bourse Régionale des Valeurs Mobilières)**.

L'approche utilise **Smolagents** pour orchestrer des outils Python déterministes. Le **CodeAgent** superviseur choisit les actions à exécuter, tandis que les fonctions Python restent fiables et testables.

---

## Architecture Générale

```
User
  ↓
run_smol_ingestion.py (Entry Point)
  ↓
CodeAgent (Superviseur Smolagents)
  ├── discover_brvm_reports()      → Scrapping BRVM
  ├── download_report_pdf()         → Téléchargement
  ├── validate_pdf_file()           → Validation
  ├── compute_file_checksum()       → Intégrité
  ├── load_existing_checksums()     → Détection doublons
  ├── save_report_metadata()        → Sauvegarde métadonnées
  └── save_ingestion_log()          → Logging
  ↓
data/ (Stockage final)
```

---

## Dossiers et Fichiers Expliqus

### 1. **app/ingest/schemas.py**
**But :** Définir la structure des données avec Pydantic

```python
class ReportDocument(BaseModel):
    source: str              # "BRVM"
    title: str              # Titre du rapport
    page_url: str           # URL de la page document
    pdf_url: str            # URL directe du PDF
    company: str | None     # Nom de l'entreprise
    year: str | None        # Année du rapport
    document_type: str | None  # Type : annual_report, financial_statements, etc.
```

**Principales fonctions :**
- Validation automatique des données JSON <-> Python
- Import dans tous les autres modules
- Garantit la cohérence des métadonnées

**Liens :**
- Utilisé par -> `brvm_tools.py`, `storage_tools.py`, `run_smol_ingestion.py`

---

### 2. **app/ingest/brvm_tools.py**
**But :** Découvrir les rapports BRVM via scraping Web

**Principales fonctions :**

| Fonction | Rôle |
|----------|------|
| `discover_brvm_reports()` | **TOOL Smolagents**. Scrape BRVM, retourne JSON de rapports |
| `extract_year()` | Extrait l'année d'un texte (regex 20XX) |
| `infer_document_type()` | Classe le type : rapport_annuel, états_financiers, etc. |
| `infer_company()` | Extrait le nom de l'entreprise du titre |
| `extract_title()` | Récupère le titre HTML de la page |
| `find_document_pages()` | Scrape les liens vers les pages de documents |
| `find_pdf_links()` | Extrait les URLs des PDFs d'une page |
| `normalize_list()` | Parse les filtres utilisateur (CSV → list) |
| `report_matches()` | Filtre les rapports par entreprise/année |

**Workflow :**
1. CodeAgent appelle `discover_brvm_reports(companies="CIE CI", years="2024")`
2. Scrape BRVM avec helpers
3. Retourne JSON stringifié avec tous les rapports découverts
4. CodeAgent parse le JSON et l'envoie aux tools suivants

**Liens :**
- Imports → `schemas.py`
- Appelé par → `run_smol_ingestion.py` (CodeAgent)
- Sortie → JSON de rapports

---

### 3. **app/ingest/quality_tools.py**
**But :** Valider la qualité des PDFs téléchargés

**Principales fonctions :**

| Fonction | Rôle |
|----------|------|
| `validate_pdf_file()` | **TOOL**. Vérifie que le fichier est un PDF valide |
| `compute_file_checksum()` | **TOOL**. Calcule le SHA256 d'un fichier |

**Validation :**
- [OK] Fichier existe
- [OK] Taille > 1KB
- [OK] Header = `%PDF-`

**Workflow :**
1. Après téléchargement d'un PDF
2. CodeAgent appelle `validate_pdf_file(local_path)`
3. Si valide → continuer
4. Si invalide → marquer comme "invalid_pdf"

**Liens :**
- Indépendant (pas d'imports internes)
- Appelé après → `download_report_pdf()`
- Entrée pour → `compute_file_checksum()`, `save_report_metadata()`

---

### 4. **app/ingest/storage_tools.py**
**But :** Télécharger, stocker et gérer les métadonnées des rapports

**Principales fonctions :**

| Fonction | Rôle |
|----------|------|
| `slugify()` | Convertit du texte en slug sûr (lowercase, no special chars) |
| `build_local_path()` | Construit le chemin d'un PDF : `data/raw/BRVM/cie_ci/2024/annual_report/report.pdf` |
| `download_report_pdf()` | **TOOL**. Télécharge un PDF, retourne le chemin local |
| `load_existing_checksums()` | **TOOL**. Scanne les manifests pour détecter les doublons |
| `save_report_metadata()` | **TOOL**. Crée un `.manifest.json` à côté du PDF |
| `save_ingestion_log()` | **TOOL**. Sauvegarde le résumé de l'ingestion |

**Structure des fichiers :**
```
data/raw/
├── BRVM/
│   ├── cie_ci/
│   │   ├── 2024/
│   │   │   ├── annual_report/
│   │   │   │   ├── rapport_annuel_2024.pdf
│   │   │   │   └── rapport_annuel_2024.pdf.manifest.json
│   │   │   └── financial_statements/
│   │
│   └── sonatel/
│       └── 2023/

data/logs/
└── ingestion_run_20260508_120000.json
```

**Exemple .manifest.json :**
```json
{
  "source": "BRVM",
  "title": "Rapport Annuel CIE CI 2024",
  "pdf_url": "https://...",
  "company": "CIE CI",
  "year": "2024",
  "document_type": "annual_report",
  "local_path": "data/raw/BRVM/cie_ci/2024/annual_report/rapport.pdf",
  "checksum_sha256": "abc123...",
  "status": "success",
  "downloaded_at": "2026-05-08 12:00:00"
}
```

**Workflow :**
1. Pour chaque rapport découvert
2. `download_report_pdf()` → télécharge
3. `validate_pdf_file()` → valide
4. `compute_file_checksum()` → intégrité
5. `load_existing_checksums()` → détecte doublon
6. `save_report_metadata()` → crée manifest
7. `save_ingestion_log()` → résumé final

**Liens :**
- Imports → néant (self-contained)
- Appelé par → `run_smol_ingestion.py` (CodeAgent)
- Crée → PDF + .manifest.json + logs JSON

---

### 5. **app/ingest/model_provider.py**
**But :** Construire le modèle LLM pour le CodeAgent

**Principales fonctions :**

| Fonction | Rôle |
|----------|------|
| `build_model()` | Crée une instance LiteLLMModel |

**Providers supportés :**
- **ollama** : Local (par défaut : `qwen2.5-coder:7b`)
- **huggingface** : Via LiteLLM (par défaut : `Qwen/Qwen2.5-Coder-32B-Instruct`)

**Usage :**
```python
model = build_model(provider="ollama", model_id="ollama/qwen2.5-coder:7b")
```

**Configuration :**
- Temperature = 0.1 (déterministe)
- Peut utiliser `OLLAMA_API_BASE` env var

**Liens :**
- Importé par → `run_smol_ingestion.py`
- Dépend de → `LiteLLMModel` (Smolagents)

---

### 6. **app/ingest/run_smol_ingestion.py**
**But :** Orchestrer l'ingestion complète via CodeAgent

**Principales fonctions :**

| Fonction | Rôle |
|----------|------|
| `main()` | Parse CLI args + crée + lance CodeAgent |

**Arguments CLI :**
```bash
--companies "CIE CI,SONATEL"   # Filtre par entreprises
--years "2023,2024"            # Filtre par années
--max-pages 5                  # Nombre de pages BRVM à scraper
--limit 10                     # Nombre max de rapports à télécharger
--provider ollama              # ollama ou huggingface
--model-id "..."               # ID du modèle
```

**Workflow du CodeAgent :**
1. Appelle `discover_brvm_reports()` → liste
2. Parse JSON, garde max `limit` rapports
3. Appelle `load_existing_checksums()` → checksums
4. **Pour chaque rapport :**
   - `download_report_pdf()` → local_path
   - `validate_pdf_file()` → valide ?
   - `compute_file_checksum()` → sha256
   - Checksum existe ? → `"duplicate"`
   - Sinon → `save_report_metadata()` → `"success"`
5. Appelle `save_ingestion_log()` → résumé JSON
6. Affiche résumé

**Liens :**
- Imports → `brvm_tools`, `quality_tools`, `storage_tools`, `model_provider`, `schemas`
- Point d'entrée → CLI `python -m app.ingest.run_smol_ingestion`

---

## Liens Entre Modules

```
run_smol_ingestion.py (CLI + CodeAgent)
    ├─→ model_provider.py (construit le LLM)
    ├─→ brvm_tools.py (découverte)
    ├─→ quality_tools.py (validation)
    ├─→ storage_tools.py (stockage)
    └─→ schemas.py (modèles)
```

**Flux de données :**
```
ReportDocument (JSON)
    ↓
brvm_tools.discover_brvm_reports()
    ↓ [JSON]
CodeAgent parse
    ↓ [dict]
storage_tools.download_report_pdf()
    ↓ [local_path]
quality_tools.validate_pdf_file() + compute_file_checksum()
    ↓ [status, checksum]
storage_tools.load_existing_checksums() [détecte doublons]
    ↓
storage_tools.save_report_metadata()
    ↓ [manifest.json]
storage_tools.save_ingestion_log()
    ↓ [ingestion_run_*.json]
```

---

## Structure des Données

### Répertoire `data/`

```
data/
raw/                           # PDFs téléchargés
  BRVM/
    {company}/{year}/{doc_type}/
      *.pdf
      *.pdf.manifest.json

metadata/                      # (Réservé pour phases futures)
  .gitkeep

logs/                          # Logs d'ingestion
  ingestion_run_20260508_120000.json
  ingestion_run_20260508_130000.json
```

---

## Checklist Phase 1

- [OK] `schemas.py` -> Modèle `ReportDocument`
- [OK] `brvm_tools.py` -> Découverte BRVM + scraping helpers
- [OK] `quality_tools.py` -> Validation PDF + checksum
- [OK] `storage_tools.py` -> Téléchargement + métadonnées + logs
- [OK] `model_provider.py` -> Construction LLM (Ollama / HuggingFace)
- [OK] `run_smol_ingestion.py` -> CodeAgent orchest rateur
- [OK] `data/` -> Structure de répertoires
- [OK] `.gitignore` -> Exclude PDFs et logs
- [OK] `requirements.txt` -> Dépendances

---

## Utilisation

### Installation
```bash
pip install -r requirements.txt
```

### Exemples d'Exécution

**1. Une entreprise, une année :**
```bash
python -m app.ingest.run_smol_ingestion \
  --provider ollama \
  --companies "CIE CI" \
  --years "2024" \
  --limit 5
```

**2. Plusieurs entreprises, plusieurs années :**
```bash
python -m app.ingest.run_smol_ingestion \
  --provider ollama \
  --companies "CIE CI,SONATEL,ORANGE CI" \
  --years "2023,2024" \
  --limit 20
```

**3. Toutes les entreprises pour 2024 :**
```bash
python -m app.ingest.run_smol_ingestion \
  --provider ollama \
  --years "2024" \
  --limit 30
```

**4. Avec HuggingFace :**
```bash
python -m app.ingest.run_smol_ingestion \
  --provider huggingface \
  --companies "CIE CI" \
  --years "2024" \
  --limit 5
```

---

## Sortie Attendue

Après exécution, vous verrez :

1. **Fichiers PDF** : `data/raw/BRVM/{company}/{year}/{doc_type}/*.pdf`
2. **Métadonnées** : `data/raw/BRVM/{company}/{year}/{doc_type}/*.pdf.manifest.json`
3. **Log d'exécution** : `data/logs/ingestion_run_*.json`

**Exemple résumé CodeAgent :**
```
Selected companies: ['cie ci']
Selected years: ['2024']
Discovered reports: 8
Downloaded successfully: 5
Duplicate reports: 2
Invalid PDFs: 1
Errors: 0
Log path: data/logs/ingestion_run_20260508_120000.json
```

---

## Prochaines Phases

- **Phase 2** : Extraction et parsing des PDFs (PyPDF, LLM-based extraction)
- **Phase 3** : Vectorisation et stockage vectoriel (Embeddings + VectorDB)
- **Phase 4** : RAG Pipeline (Retrieval + LLM Answering)
- **Phase 5** : Agent Analyst (Multi-tool Financial Agent)

---

## 📝 Notes Importantes

1. **Scraping déterministe** : Pas d'hallucinations. Smolagents orchestre du code Python fiable.
2. **Erreurs gérées** : Timeouts, PDFs corrompus, doublons → tous loggés.
3. **Résilience** : Les manifests existent même pour les PDFs invalides.
4. **Scalabilité** : Peut être étendu pour traiter des milliers de rapports.

---

**Créé** : Phase 1 - Collecte et Stockage  
**Version** : 1.0  
**Dernière mise à jour** : 2026-05-08
