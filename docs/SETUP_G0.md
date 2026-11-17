# G0 — Installation et validation reproductible (2026-11-17)

## Portée et limites

Le dépôt cible **Python 3.11**. `requirements.txt` et `requirements-dev.txt`
contiennent des versions **directes exactes** (`==`), mais **pas encore les
versions transitives**. Un vrai lock résolu avec hash, `requirements.lock`, est
prévu par `make lock` et doit être généré sur une machine ayant accès à PyPI,
commité puis validé en CI. **Ne pas déclarer G0 entièrement validé avant ça.**
Les modèles Hugging Face et Ollama sont des artefacts externes distincts des
paquets Python. Ils ne sont pas téléchargés pendant l'installation ni les tests.

## Prérequis système

- Python **3.11** et `python3.11 -m venv`; `git` pour cloner.
- Au moins 8 Go de RAM conseillés pour le LLM `qwen2.5:7b` : la consommation
  exacte dépend du modèle et de sa quantification.
- Tesseract OCR et langues `fra` + `eng` pour les PDF scannés.
- Ollama et `qwen2.5:7b` uniquement pour exécuter la génération locale.
- Accès Internet au **premier** setup pour pip, Ollama et Hugging Face.

Ubuntu / Debian :

```bash
sudo apt-get update
sudo apt-get install -y git tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng
```

Pour Python 3.11, utiliser une distribution Python dédiée (`python.org`, `pyenv`
ou `uv python install 3.11`) si le gestionnaire de paquets de la
distribution ne propose pas cette version. Installer aussi son module `venv`.

macOS : installer Python 3.11, Git, et `brew install tesseract tesseract-lang`.
Windows : privilégier WSL2 Ubuntu pour reproduire la même procédure.
Ollama : https://ollama.com/download (installation à effectuer séparément).
Pour vérifier Python et la résolution des dépendances avant d'installer :
`python3.11 --version` puis `python3.11 -m pip --version`.

## Clone, installation, tests

```bash
git clone https://github.com/BeediGoua/Agentic-Financial-RAG-Analyst.git
cd Agentic-Financial-RAG-Analyst
bash scripts/bootstrap.sh
# Ou, ensuite, exécuter uniquement les tests :
bash scripts/test.sh
# Équivalent : make test
```

Le bootstrap crée `.venv` sans accès aux paquets globaux, installe les
requirements, exécute `pip check`, puis lance les tests. En cas d'échec, il sort
avec un code différent de zéro. Le fonctionnement du test ne dépend pas des
PDF BRVM, d'Ollama ni de modèles Hugging Face téléchargés.

`PYTHON_BIN=python3.12 bash scripts/bootstrap.sh` peut servir à tester une
autre version, mais **Python 3.11 reste la cible de référence**.

## Diagnostic du système complet

```bash
.venv/bin/python scripts/check_env.py --profile core --strict
.venv/bin/python scripts/check_env.py --profile full
# Un échec sera signalé par le code de sortie :
.venv/bin/python scripts/check_env.py --profile full --strict
```

Le mode `full` vérifie `tesseract`, les langues OCR `fra`/`eng`, le binaire
Ollama, l'API locale, la présence de `qwen2.5:7b` et deux modèles HF en cache.
Aucune de ces vérifications ne déclenche de téléchargement. Le mode non strict
présente les éléments manquants pour aider au diagnostic.

Pour installer les poids au préalable :

```bash
ollama serve              # autre terminal, si non lancé par le système
ollama pull qwen2.5:7b
.venv/bin/python scripts/prefetch_models.py
# Les quatre modèles du catalogue, si nécessaire :
.venv/bin/python scripts/prefetch_models.py --all
bash scripts/test.sh --full
```

Modèles HF utilisés par défaut :
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` ;
- `cross-encoder/ms-marco-TinyBERT-L-2-v2`.

Autres variantes dans `app/embeddings/models.py` et `app/reranking/models.py`.
En production, verrouiller aussi les **revisions/commits des modèles HF**, car
une simple chaîne de nom ne garantit pas des poids identiques dans le temps.

## Génération du lock complet (étape bloquante encore ouverte)

Sur une machine connectée disposant de `uv` :

```bash
make lock
# Vérifier ensuite l'installation depuis zéro, sur Python 3.11 :
rm -rf .venv
bash scripts/bootstrap.sh
```

`requirements.lock` sera préféré par `bootstrap.sh` quand il est présent.
La CI enregistre également un `pip freeze` en artefact pour l'audit, mais **un
`pip freeze` CI n'est pas un substitut à un lock versionné et validé**.

## Références de configuration

- `requirements.txt` : packages runtime directement utilisés, versions épinglées ;
- `requirements-dev.txt` : pytest ;
- `.env.example` : paramètres et nom du modèle Ollama cohérents avec le code ;
- `scripts/check_env.py` : diagnostic des versions, binaires, modèles et service ;
- `scripts/test.sh` : commande unique de tests hors ligne ;
- `.github/workflows/g0-ci.yml` : tests d'installation sur Ubuntu/Python 3.11 ;
- `docs/JOURNAL_G0.md` : journal des décisions, changements et limites.

## Éléments hors du périmètre G0

Correction des erreurs silencieuses d'ingestion, fiabilité du retrieval, citations,
indexation FAISS, métriques de qualité et tests sur les vrais documents BRVM :
ce sont des tâches des gates G1 à G4. La présence de tests G0 ne valide pas
scientifiquement les résultats financiers générés.
