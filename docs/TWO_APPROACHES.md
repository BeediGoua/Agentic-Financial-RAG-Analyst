# Phase 1 - Two Approaches to Ingestion

## Approche 1: Simple Ingestion (RECOMMANDEE pour tester Phase 1)

**Pas besoin de LLM du tout!** Les tools BRVM fonctionnent directement.

```bash
python simple_ingest.py \
  --companies "CIE CI" \
  --years "2024" \
  --limit 5
```

### Avantages
- [OK] **Zéro dépendance LLM** - Fonctionne tout de suite
- [OK] **Rapide** - Exécution directe des tools
- [OK] **Transparent** - Voir chaque étape
- [OK] **Parfait pour tester** - La vraie logique d'ingestion

### Sortie à attendre
```
[1/6] 🔍 Discovering BRVM reports...
     ✅ Found 3 reports
[2/6] 📋 Loading existing checksums...
     ✅ Found 0 existing checksums
[3/6] Report 1/3: CIE CI Annual Report 2024...
     📥 Downloading PDF...
     ✅ Downloaded to: data/raw/BRVM/cie_ci/2024/annual_report/rapport.pdf
     🔍 Validating PDF...
     ✅ PDF is valid
     🔐 Computing checksum...
     ✅ Checksum: abc123def456...
     💾 Saving metadata...
     ✅ Metadata: data/raw/BRVM/cie_ci/2024/annual_report/rapport.pdf.manifest.json
[6/6] 📝 Saving ingestion log...
     ✅ Log saved: data/logs/ingestion_run_20260508_120000.json

SUMMARY
=======
Total processed:       3
✅ Successful:         3
⚠️  Duplicates:        0
❌ Invalid PDFs:       0
🔴 Errors:            0
```

---

## Approche 2: CodeAgent Orchestration (Optionnel)

Si vous voulez l'orchestration par LLM (CodeAgent), utiliser le fallback automatique:

```bash
python -m app.ingest.run_smol_ingestion \
  --provider auto \
  --companies "CIE CI" \
  --years "2024" \
  --limit 5
```

### Qu'est-ce qui se passe avec `auto`

```
🔍 Auto-detecting LLM provider...

  Essai 1: Ollama sur localhost:11434?
    ✅ OUI → Utilise Ollama local
    ❌ NON → Essai suivant

  Essai 2: HuggingFace token configuré?
    ✅ OUI → Utilise HuggingFace API
    ❌ NON → Erreur avec solutions

  Si les deux échouent:
    ❌ Erreur avec instructions pour configurer
```

### Configuration des providers

#### Ollama (Local)
```bash
# Terminal 1: Démarrer le serveur
ollama serve

# Terminal 2: Tirer le modèle (une fois)
ollama pull qwen2.5-coder:7b

# Terminal 3: Lancer l'ingestion (détectera automatiquement)
python -m app.ingest.run_smol_ingestion --companies "CIE CI"
```

#### HuggingFace (Cloud)
```bash
# 1. Obtenir un token: https://huggingface.co/settings/tokens
# 2. Configurer
export HUGGINGFACE_API_KEY="hf_votre_token_tres_long_ici"

# 3. Lancer (détectera automatiquement)
python -m app.ingest.run_smol_ingestion --companies "CIE CI"
```

### Avantages
- [OK] Fallback automatique (Ollama -> HuggingFace)
- [OK] LLM orchestre les tools intelligemment
- [OK] Utile pour étapes futures plus complexes

### Inconvénients
- [LIMITATION] Nécessite une config LLM
- [LIMITATION] Plus lent (communication avec LLM)
- [LIMITATION] Pas nécessaire pour Phase 1

---

## 📊 Comparaison

| Aspect | Simple | CodeAgent |
|--------|--------|-----------|
| **Démarrage** | Immédiat | Nécessite LLM |
| **Vitesse** | Rapide | Moyen (appels LLM) |
| **Reconnaissance erreurs** | OK | Meilleure |
| **Transparence** | Très claire | Blackbox LLM |
| **Phase 1?** | [OK] OUI | [?] Optionnel |
| **Pour tester tools** | [OK] OUI | [NOT NEEDED] Overkill |
| **Pour Phase 2+** | [LIMITATION] Peut suffi r | [OK] OUI |

---

## Recommandation

### Pour cette étape (Phase 1):
```bash
# [RECOMMENDED] - Testez simple_ingest.py d'abord!
python simple_ingest.py --companies "CIE CI" --years "2024"
```

### Quand utiliser CodeAgent:
- Phase 2: Parsing PDF complexe
- Phase 3: Indexation vectorielle  
- Phase 4: RAG with knowledge
- Phase 5: Multi-tool financial agent

---

## 🔧 Fallback Automatique Expliqué

```python
# Dans model_provider.py
def build_model(provider="auto"):
    if provider == "auto":
        # Essai 1: Ollama
        if ollama_running():
            return LiteLLMModel(model="ollama/...", api_base="http://localhost:11434")
        
        # Essai 2: HuggingFace
        if huggingface_token_exists():
            return LiteLLMModel(model="Qwen/Qwen2.5-Coder-32B-Instruct")
        
        # Éch dans les deux cas
        raise HelpfulError(
            "Please configure Ollama or HuggingFace token"
        )
```

---

## 📋 Checklist - Simple Ingestion

- [ ] Dépendances installées: `pip install -r requirements.txt`
- [ ] Structure `data/` créée ✅
- [ ] Exécuter: `python simple_ingest.py`
- [ ] Vérifier: `ls data/raw/BRVM/*/`
- [ ] Vérifier logs: `ls data/logs/`

**Durée totale:** ~2 minutes

---

## 📋 Checklist - CodeAgent avec Fallback

- [ ] Dépendances installées
- [ ] (Optionnel) Ollama: `ollama serve` + `ollama pull qwen2.5-coder:7b`
- [ ] OU HuggingFace: `export HUGGINGFACE_API_KEY=...`
- [ ] Exécuter: `python -m app.ingest.run_smol_ingestion --provider auto`

**Durée totale:** ~5 minutes + config LLM

---

## 🚨 Troubleshooting

### "No LLM provider found"
→ Vous utilisez CodeAgent mais n'avez configuré ni Ollama ni HuggingFace  
→ **Solution:** Utilisez `simple_ingest.py` à la place!

### Connection refused
→ Ollama démarre mais pas accessible  
→ **Solution:** Relancer: `ollama serve --host 0.0.0.0:11434`

### Invalid HuggingFace token
→ Token manquant ou expiré  
→ **Solution:** Régénérer sur https://huggingface.co/settings/tokens

---

## 🎓 Ce qu'on apprend

**Les tools ne dépendent PAS du LLM.** Le LLM n'est qu'un superviseur pour orchestrer.

Phase 1 = Data Collection → **Les tools purs (BRVM scraping, validation, stockage)**  
Phase 2+ = Data Processing → **CodeAgent + Tools pour logique complexe**

Pour Phase 1, on utilise juste les tools directement. C'est plus simple et plus rapide.

---

**TL;DR:**
```bash
# ⭐ Testez d'abord ça (pas d'LLM requis)
python simple_ingest.py

# Puis optionnellement, orchestration avec LLM
python -m app.ingest.run_smol_ingestion --provider auto
```
