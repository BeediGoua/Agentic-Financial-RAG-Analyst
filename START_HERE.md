# Phase 1 - PRÊT À TESTER

## État Actuel

```
[OK] Architecture complète implémentée
[OK] Tools testés et validés  
[OK] 2 approches disponibles
[OK] Documentation exhaustive
[NOT NEEDED] Pas de LLM configuré (NORMAL pour Phase 1!)
```

---

## MAINTENANT: Exécutez CECI

### Option A: Mode Simple (RECOMMANDÉ - Pas d'LLM)

```bash
cd /workspaces/Agentic-Financial-RAG-Analyst
python simple_ingest.py --companies "CIE CI" --years "2024" --limit 2
```

Ou via le script:
```bash
bash run_phase1.sh
```

**Qu'est-ce que ça fait:**
- Scrape BRVM pour trouver les rapports
- Télécharge les PDFs
- Valide les fichiers PDF
- Calcule les checksums
- Sauvegarde les métadonnées
- Génère le log d'ingestion

**Durée:** ~30-60 secondes par rapport

---

### Option B: Avec Orchestration LLM (Optionnel pour phases futures)

Si vous voulez que l'LLM orchestre:

#### Configuration Ollama (local - optionnel)
```bash
# Terminal 1: Démarrer Ollama
ollama serve

# Terminal 2: Tirer le modèle
ollama pull qwen2.5-coder:7b

# Terminal 3: Lancer l'ingestion (détecte auto Ollama)
python -m app.ingest.run_smol_ingestion \
  --companies "CIE CI" --years "2024" --limit 2
```

#### Configuration HuggingFace (cloud - optionnel)
```bash
# 1. Obtenir token: https://huggingface.co/settings/tokens
# 2. Configurer variable
export HUGGINGFACE_API_KEY="hf_votre_token_ici"

# 3. Lancer (détecte auto HuggingFace)
python -m app.ingest.run_smol_ingestion \
  --companies "CIE CI" --years "2024" --limit 2
```

---

##  Résultats Attendus

### Avec `simple_ingest.py`:

```
====================================
AGENTIC FINANCIAL RAG - SIMPLE INGESTION
====================================

[1/6] Discovering BRVM reports...
     [OK] Found X reports

[2/6] Loading existing checksums...
     [OK] Found X checksums

[3/6] Report 1/X: ...
     Downloading PDF...
     [OK] Downloaded to: data/raw/BRVM/cie_ci/2024/annual_report/...pdf
     Validating PDF...
     [OK] PDF is valid
     Computing checksum...
     [OK] Checksum: abc123...
     Saving metadata...
     [OK] Metadata: ...pdf.manifest.json

[6/6] Saving ingestion log...
     [OK] Log saved: data/logs/ingestion_run_XXXXXXX.json

====================================
SUMMARY
====================================
Total processed:       2
[OK] Successful:       2
[WARNING] Duplicates:  0
[ERROR] Invalid PDFs:  0
[ERROR] Errors:        0

[OK] 2 report(s) successfully ingested!
Location: data/raw/BRVM/
Metadata: *.pdf.manifest.json files
```

### Fichiers créés:
```
data/raw/BRVM/
cie_ci/
  2024/
    annual_report/
      rapport_annuel_2024.pdf
      rapport_annuel_2024.pdf.manifest.json
    financial_statements/
      ...

data/logs/
  ingestion_run_20260508_120000.json
```

---

##  Vérifier les Résultats

```bash
# Voir les PDFs téléchargés
tree data/raw/BRVM/ -L 4

# Voir un fichier manifeste (métadonnées)
cat data/raw/BRVM/cie_ci/2024/annual_report/*.manifest.json

# Voir le log d'ingestion
cat data/logs/ingestion_run_*.json | jq
```

---

## Documentation de Référence

| Document | Sujet |
|----------|-------|
| [QUICKSTART.md](docs/QUICKSTART.md) | Guide 5 min |
| [PHASE_1.md](docs/PHASE_1.md) | Architecture détaillée |
| [TWO_APPROACHES.md](docs/TWO_APPROACHES.md) | Simple vs CodeAgent |
| [SETUP_TROUBLESHOOTING.md](docs/SETUP_TROUBLESHOOTING.md) | Dépannage |
| [ANALYSIS_SUMMARY.md](docs/ANALYSIS_SUMMARY.md) | Analyse technique |

---

## Quick Commands

```bash
# Test tools (même approche que simple_ingest mais suite de tests)
python test_tools.py

# Simple ingestion (RECOMMANDÉ)
python simple_ingest.py --companies "CIE CI" --years "2024"

# Simple avec script
bash run_phase1.sh

# CodeAgent avec fallback auto (nécessite Ollama OU HuggingFace)
python -m app.ingest.run_smol_ingestion --provider auto --companies "CIE CI"

# CodeAgent Ollama spécifiquement
python -m app.ingest.run_smol_ingestion --provider ollama --companies "CIE CI"

# CodeAgent HuggingFace spécifiquement
python -m app.ingest.run_smol_ingestion --provider huggingface --companies "CIE CI"
```

---

## Comprendre la Différence

### `simple_ingest.py` (Simple Mode)
```
Utilisateur
    ↓
Python code
    ↓
Direct function calls
    ↓
BRVM tools exécutés
    ↓
Résultats
```

**Avantages:**
- [OK] Zéro dépendance externe
- [OK] Transparent et rapide
- [OK] Parfait pour tests
- [OK] Idéal Phase 1

---

### `run_smol_ingestion.py` (CodeAgent Mode)
```
Utilisateur
    ↓
Python code
    ↓
CodeAgent (orchestrator)
    ↓
Appelle LLM pour décisions
    ↓
LLM choisit tools
    ↓
Tools exécutés
    ↓
Résultats
```

**Avantages:**
- [OK] Orchestration intelligente
- [OK] Gestion erreurs meilleure
- [OK] Scalable pour Phase 2+
- [LIMITATION] Nécessite LLM

---

## Checklist Finale

- [ ] Dépendances installées: `pip install -r requirements.txt`
- [ ] Répertoires créés: `data/{raw,logs,metadata}`
- [ ] Code Python valide
- [ ] Tests validés: `python test_tools.py`
- [ ] EXECUTER: `python simple_ingest.py "CIE CI" "2024"`
- [ ] Verifier: `ls -R data/raw/`
- [ ] Verifier: `ls data/logs/`

---

## Prochaines Étapes

**Après Phase 1 (une fois les PDFs téléchargés):**

1. **Phase 2** - Extraction PDF
   - PyPDF2 / pdfplumber
   - Text extraction + tables
   - Cleaning & normalization

2. **Phase 3** - Vectorisation
   - Embedding models (Sentence-Transformers)
   - VectorDB (Chroma, Pinecone, Weaviate)
   - Indexing

3. **Phase 4** - RAG Pipeline
   - Retrieval (semantic search)
   - LLM generation
   - Multi-source answers

4. **Phase 5** - Agent Financier
   - Multi-tool orchestration
   - Financial analysis
   - Natural language finance

---

## Résumé

Phase 1 est **100% ENTIÈREMENT TESTABLE** sans aucune dépendance LLM.

**Start here:**
```bash
python simple_ingest.py --companies "CIE CI" --years "2024" --limit 2
```

---

# 1. Vérifier les tools
python test_tools.py

# 2. Test ingestion complète
python simple_ingest.py --companies "CIE CI" --years "2024" --limit 2

# 3. Vérifier résultats
ls data/raw/BRVM/