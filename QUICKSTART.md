# Quick Start Guide - Agentic Financial RAG Analyst

## [1] Installation des dépendances

```bash
pip install -r requirements.txt
```

---

## [2] Vérifier que les tools fonctionnent

**Avant de lancer l'orchestration complète**, testez les tools individuellement:

```bash
python test_tools.py
```

Cela vérifiera:
- [OK] Découverte des rapports BRVM
- [OK] Validation des PDFs
- [OK] Calcul des checksums
- [OK] Sauvegarde des métadonnées

**Output attendu:**
```
TEST SUMMARY
============
BRVM Discovery: [OK] PASS
Storage Functions: [OK] PASS
Checksum Functions: [OK] PASS

[SUCCESS] All core tools are working!
```

---

## [3] Configurer un LLM

Le CodeAgent nécessite un modèle LLM pour orchestrer les tools.

### Option A: Ollama (Recommandé - Local)

```bash
# 1. Installer Ollama
# Télécharger depuis https://ollama.ai
# Ou: brew install ollama (macOS) / apt install ollama (Linux)

# 2. Lancer le serveur
ollama serve

# 3. Dans un autre terminal, tirer le modèle
ollama pull qwen2.5-coder:7b

# 4. Tester la connexion
curl http://localhost:11434/api/tags
```

### Option B: HuggingFace (Cloud - Pas de setup local)

```bash
# 1. Créer un compte et obtenir un token:
# https://huggingface.co/settings/tokens

# 2. Configurer le token
export HUGGINGFACE_API_KEY="hf_votre_token_tres_long_ici"

# 3. C'est prêt! Pas besoin de modèle local
```

---

## [4] Lancer l'ingestion

### Avec Ollama:
```bash
python -m app.ingest.run_smol_ingestion \
  --provider ollama \
  --companies "CIE CI" \
  --years "2024" \
  --limit 5
```

### Avec HuggingFace:
```bash
HUGGINGFACE_API_KEY="hf_..." python -m app.ingest.run_smol_ingestion \
  --provider huggingface \
  --companies "CIE CI" \
  --years "2024" \
  --limit 5
```

---

## 📊 Exemples d'usage

### Une entreprise, une année
```bash
python -m app.ingest.run_smol_ingestion \
  --companies "CIE CI" \
  --years "2024" \
  --limit 10
```

### Plusieurs entreprises
```bash
python -m app.ingest.run_smol_ingestion \
  --companies "CIE CI,SONATEL,ORANGE CI" \
  --years "2023,2024" \
  --limit 20
```

### Toutes les entreprises disponibles
```bash
python -m app.ingest.run_smol_ingestion \
  --years "2024" \
  --limit 50
```

### Personnalisé
```bash
python -m app.ingest.run_smol_ingestion \
  --provider ollama \
  --companies "CIE CI,SONATEL" \
  --years "2023,2024,2025" \
  --max-pages 10 \
  --limit 15
```

---

## 📁 Résultats

Les fichiers téléchargés seront organisés comme suit:

```
data/raw/
BRVM/
  cie_ci/
    2024/
      annual_report/
        rapport_annuel_2024.pdf
        rapport_annuel_2024.pdf.manifest.json
      financial_statements/
  sonatel/
    2024/
      ...
data/logs/
  ingestion_run_20260508_120000.json
  ingestion_run_20260508_130000.json
```

Chaque PDF a un fichier `.manifest.json` avec les métadonnées:

```json
{
  "source": "BRVM",
  "title": "Rapport Annuel CIE CI 2024",
  "company": "CIE CI",
  "year": "2024",
  "document_type": "annual_report",
  "checksum_sha256": "abc123...",
  "status": "success",
  "downloaded_at": "2026-05-08 12:00:00"
}
```

---

## References

- [Phase 1 Details](docs/PHASE_1.md) - Architecture complète
- [Setup & Troubleshooting](docs/SETUP_TROUBLESHOOTING.md) - Guide dépannage
- [README](README.md) - Original project README

---

## Performance Tips

### Pour Ollama
- **GPU recommandé** pour performance (8GB VRAM minimum)
- **Temps de démarrage:** 10-30 secondes
- **Vitesse:** 1 rapport = 10-30 secondes (avec scraping)

### Pour HuggingFace
- **Pas de GPU requis** (tout est en cloud)
- **Temps de démarrage:** Immédiat
- **Vitesse:** Dépend de la latence réseau

### Optimisations
```bash
# Réduire le nombre de pages à scraper
--max-pages 2

# Tester avec juste 1-2 rapports
--limit 2

# Vérifier d'abord les tools
python test_tools.py  # ~5 secondes
```

---

## 🆘 Problèmes fréquents

### [ERROR] "Connection refused [Errno 111]"
[CAUSE] Ollama n'est pas en cours d'exécution  
[SOLUTION] Lancez `ollama serve` dans un autre terminal

### [ERROR] "Invalid API token"
[CAUSE] Token HuggingFace incorrect ou expiré  
[SOLUTION] Régénérez-le sur https://huggingface.co/settings/tokens

### [ERROR] "No module named 'smolagents'"
[CAUSE] Dépendances non installées  
[SOLUTION] Exécutez `pip install -r requirements.txt`

### [ERROR] "No such file or directory: data/raw"
[CAUSE] Structure des répertoires non créée  
[SOLUTION] Exécutez `python -c "from app.ingest import *;"` ou créez les dossiers manuellement

---

## Checklist avant de lancer

- [ ] Dépendances installées: `pip install -r requirements.txt`
- [ ] Tools testés: `python test_tools.py`
- [ ] LLM configuré (Ollama OU HuggingFace)
- [ ] Ollama accessible: `curl http://localhost:11434/api/tags`
- [ ] OU HuggingFace token configuré: `echo $HUGGINGFACE_API_KEY`
- [ ] Dossiers de données créés

```bash
# One-line setup check
python test_tools.py && echo "[OK] Ready!" || echo "[ERROR] Check errors above"
```

---

## Prochaines étapes

1. **Phase 1 Complete** ✅ - Ingestion & Stockage
2. **Phase 2** - Extraction & Parsing PDF
3. **Phase 3** - Vectorisation & VectorDB
4. **Phase 4** - RAG Pipeline
5. **Phase 5** - Financial Analyst Agent

Voir [PHASE_1.md](docs/PHASE_1.md) pour les détails.

---

**Status:** Phase 1 - Data Collection & Storage ✅  
**Last Updated:** 2026-05-08  
**Version:** 1.0.0
