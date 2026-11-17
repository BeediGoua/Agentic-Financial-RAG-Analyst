# G0 — Environnement reproductible

## Environnement obligatoire

La référence est **Python 3.11**. Le bootstrap crée une `.venv` isolée,
installe les dépendances depuis `requirements.lock` et échoue si une `.venv`
existante utilise une autre version Python. Pour corriger une `.venv` invalide,
supprimez-la explicitement puis relancez `make setup`.

Sur Codespaces, `.devcontainer/devcontainer.json` installe Tesseract et les
langues `fra`/`eng`, puis lance le setup. Sur Ubuntu/Debian :

```bash
sudo apt-get update
sudo apt-get install -y git tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng
```

Depuis la racine du dépôt :

```bash
make setup
make test
make doctor
```

`make test` n'utilise pas de données BRVM, ne contacte pas Ollama et ne
télécharge aucun modèle. `make doctor` vérifie Python 3.11, la `.venv`, les
versions Python épinglées, Tesseract et ses langues française et anglaise.
Toute anomalie fait échouer ces commandes. Le lock est ciblé Python 3.11 et
les roues disponibles pour la plateforme Linux x86_64 de référence; d'autres
plateformes peuvent avoir des roues natives différentes.

## Dépendances externes d'inférence (facultatives)

Le diagnostic séparé vérifie l'installation Ollama, son API, le modèle
`qwen2.5:7b`, son digest, ainsi que les quatre modèles HF et leurs révisions
exactes en cache. Il ne télécharge rien :

```bash
make doctor-full
# Pour un code d'échec si un service ou modèle manque :
.venv/bin/python scripts/check_env.py --profile full --strict
```

Un échec en l'absence d'Ollama ou de poids HF est normal et ne bloque pas la
CI G0. Le rapport affiche séparément chaque modèle, son identifiant, sa
révision épinglée et son état local.

### Ollama

Installez Ollama depuis [ollama.com/download](https://ollama.com/download),
démarrez son service, puis téléchargez explicitement le modèle :

```bash
ollama serve
# Dans un autre terminal :
ollama pull qwen2.5:7b
curl -s http://localhost:11434/api/tags
```

La réponse `/api/tags` expose le digest du modèle installé. Pour faire vérifier
ce digest par le diagnostic, renseignez `OLLAMA_MODEL_DIGEST` dans
l'environnement (copiez la valeur `digest` exacte, préfixe `sha256:` inclus),
puis lancez `make doctor-full`. Sans digest configuré, le diagnostic rapporte
la valeur observée sans prétendre verrouiller l'artefact. Après un changement
de quantification ou une mise à jour voulue, vérifiez et remplacez explicitement
ce digest. Le digest est déterminé par le modèle réellement tiré, et ne peut
pas être présumé avant le téléchargement.

### Modèles Hugging Face

Les quatre modèles définis dans `app/embeddings/models.py` et
`app/reranking/models.py` ont chacun une révision Git de 40 caractères épinglée
dans leur configuration. Les loaders et le préchargement emploient ces
révisions plutôt que la branche mobile `main`.

Téléchargement explicite uniquement, après installation :

```bash
.venv/bin/python scripts/prefetch_models.py --all
make doctor-full
```

Les modèles peuvent être volumineux. `make doctor-full` ne les télécharge
jamais et vérifie leur présence en cache à la révision épinglée. Pour changer
une révision, vérifiez d'abord le commit du dépôt sur Hugging Face, mettez à
jour le champ `revision` correspondant, puis régénérez/vérifiez le cache.

## Lock et plateforme

`requirements.lock` est généré par `uv pip compile --python-version 3.11
--generate-hashes` à partir de `requirements.txt` et `requirements-dev.txt`.
Après modification de ces fichiers, installez `uv`, exécutez `make lock`, puis
validez l'installation dans un environnement propre avec `make setup`,
`make test` et `make doctor`.

Le lock couvre les versions et hashes des distributions Python pour Python
3.11. Il ne verrouille ni Tesseract/les paquets système, ni Ollama, ni les
modèles eux-mêmes. Les révisions HF et le digest Ollama sont des verrous
distincts, documentés ci-dessus.
