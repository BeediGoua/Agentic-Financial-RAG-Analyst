# 🚨 Dépannage : Erreur de Connexion Ollama

## Problème

```
litellm.APIConnectionError: OllamaException - [Errno 111] Connection refused
```

Cela signifie que **Ollama n'est pas en cours d'exécution** sur `localhost:11434`.

---

## ✅ Solutions

### **Option 1: Lancer Ollama Server** (Recommandé pour dev local)

#### Installer Ollama
```bash
# Télécharger depuis https://ollama.ai
# Ou via package manager

# Ubuntu/Linux
curl https://ollama.ai/install.sh | sh

# macOS
brew install ollama
```

#### Lancer Ollama en arrière-plan
```bash
# Terminal 1: Démarrer le serveur
ollama serve

# Terminal 2: Tirer le modèle
ollama pull qwen2.5-coder:7b

# Terminal 3: Lancer l'ingestion
python -m app.ingest.run_smol_ingestion \
  --provider ollama \
  --companies "CIE CI" \
  --years "2024" \
  --limit 5
```

Vérifier que Ollama est accessible:
```bash
curl http://localhost:11434/api/tags
# Devrait retourner un JSON avec les modèles disponibles
```

---

### **Option 2: Utiliser HuggingFace API** (Cloud, pas de local setup)

#### 1. Créer un compte HuggingFace
- Aller sur https://huggingface.co
- Créer un compte gratuit
- Générer un token API (Settings → Access Tokens)

#### 2. Installer la dépendance
```bash
pip install huggingface-hub
```

#### 3. Configurer le token
```bash
export HUGGINGFACE_API_KEY="votre_token_ici"
```

#### 4. Lancer l'ingestion
```bash
python -m app.ingest.run_smol_ingestion \
  --provider huggingface \
  --model-id "meta-llama/Llama-2-13b-chat-hf" \
  --companies "CIE CI" \
  --years "2024" \
  --limit 5
```

**Modèles recommandés:**
- `Qwen/Qwen2.5-Coder-32B-Instruct` (gratuit, performant)
- `meta-llama/Llama-2-13b-chat-hf` (open source)
- `mistralai/Mistral-7B-Instruct-v0.1` (léger)

---

### **Option 3: Tester les Tools sans LLM** (Development)

Les tools eux-mêmes ne dépendent **pas** du LLM. Vous pouvez les tester indépendamment:

```bash
python test_tools.py
```

Cela testera:
- ✅ Découverte BRVM
- ✅ Validation PDF
- ✅ Calcul checksums
- ✅ Stockage métadonnées

---

### **Option 4: Docker (Isolation complète)**

Si vous avez Docker:

```bash
# Lancer Ollama dans Docker
docker run -d \
  --name ollama \
  -p 11434:11434 \
  ollama/ollama

# Tirer le modèle
docker exec ollama ollama pull qwen2.5-coder:7b

# Exécuter l'ingestion
python -m app.ingest.run_smol_ingestion \
  --provider ollama \
  --companies "CIE CI" \
  --years "2024"
```

---

## 🔍 Diagnostic

Avant d'exécuter, vérifiez votre configuration:

```bash
# Vérifier Ollama
curl -X GET http://localhost:11434/api/tags 2>/dev/null && echo "✅ Ollama OK" || echo "❌ Ollama not running"

# Vérifier HuggingFace token
echo $HUGGINGFACE_API_KEY | wc -c  # Doit être > 10 caractères

# Vérifier les dépendances
python -c "import smolagents; print(f'Smolagents: OK')"
python -c "import requests; print(f'Requests: OK')"
```

---

## 📊 Comparaison des Options

| Option | Avantages | Inconvénients | Coût |
|--------|-----------|--------------|------|
| Ollama | Local, rapide, gratuit | Nécessite installation, GPU recommandé | Gratuit |
| HuggingFace | Cloud, pas de setup, gratuit | Internet requis, limites d'API | Gratuit (limité) |
| Docker | Isolation, reproductibilité | Nécessite Docker | Gratuit |
| Tests (test_tools.py) | Vérifie la logique sans LLM | Ne teste pas l'orchestration | Gratuit |

---

## 🚀 Recommandations

### Pour développement local rapide:
```
→ Utilisez `ollama` + `test_tools.py`
```

### Pour testing CI/CD:
```
→ Utilisez les tests unitaires (test_tools.py)
```

### Pour production:
```
→ Utilisez HuggingFace API ou un service cloud LLM
```

### Pour prototypage rapide:
```
→ Testez d'abord les tools avec `test_tools.py`
→ Puis l'orchestration avec `--provider ollama`
```

---

## 🆘 Troubleshooting Avancé

### Ollama démarre mais "[Errno 111] Connection refused"

**Cause:** Le port 11434 n'est pas accessible

```bash
# Vérifier le port
netstat -tuln | grep 11434

# Si le port est occupé, arrêter le processus
lsof -i :11434
kill -9 <PID>

# Redémarrer Ollama
ollama serve --host 0.0.0.0:11434
```

### Timeout lors du téléchargement du modèle

```bash
# Augmenter le timeout et relancer
OLLAMA_HOST=0.0.0.0:11434 ollama pull qwen2.5-coder:7b
```

### HuggingFace: "Invalid API token"

```bash
# Vérifier le token
curl -H "Authorization: Bearer $HUGGINGFACE_API_KEY" \
  https://huggingface.co/api/whoami

# Régénérer le token sur https://huggingface.co/settings/tokens
```

---

## 📚 Documentation Additionnelle

- [Ollama Docs](https://github.com/ollama/ollama)
- [HuggingFace Inference API](https://huggingface.co/inference-api)
- [Smolagents Docs](https://github.com/huggingface/smolagents)
- [LiteLLM Docs](https://docs.litellm.ai/)

