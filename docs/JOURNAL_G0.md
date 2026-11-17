# Journal technique — G0 : environnement reproductible et validation

Date de finalisation : 17 novembre 2026
Dépôt : `BeediGoua/Agentic-Financial-RAG-Analyst`
Branche de travail : `chore/g0-reproducible-env-20261117`
Base de référence auditée : `main` / `a869755cc88c132f69a93aae7593d8e20413937e`

## Objectif

Rendre l'environnement de développement entièrement reproductible sur Python 3.11, verrouiller les dépendances avec un lock hashé `requirements.lock`, automatiser les tests et le diagnostic, puis valider la procédure sur une machine Codespaces réelle.

## Modifications principales

| Fichier | Problème initial | Correction appliquée | Vérification | Résultat |
| --- | --- | --- | --- | --- |
| `requirements.txt` | Versions directes non verrouillées et doublons de dépendances ; `chromadb` mentionné alors que le code n'implémente pas de backend Chroma | Épinglage exact des packages runtime et suppression du backend absent | `python -m pip check` + `scripts/check_env.py --profile core` | OK |
| `requirements-dev.txt` | Outil de test non explicitement versionné | Ajout d'un pin `pytest==9.0.2` et `pytest-cov==7.0.0` | `pytest -q tests` | OK |
| `.python-version` | Cible Python non documentée ; le dépôt n'exigeait pas explicitement 3.11 | Ajout d'un point d'entrée explicite `3.11` pour les outils locaux et IDE | `python3.11 --version` | OK |
| `.env.example` | Exemple de config incohérent avec le générateur Ollama et le modèle réel du projet | Alignement sur `qwen2.5:7b` et suppression du faux token HF | Lecture du code `app/generation/ollama_generator.py` et tests | OK |
| `scripts/bootstrap.sh` | Le bootstrap pouvait accepter une mauvaise version Python ou ignorer les échecs de dépendances | Vérification stricte `3.11 <= Python <3.14`, création d'une `.venv` isolée, installation du lock si présent, `pip check`, `scripts/test.sh` | `make setup` | OK |
| `scripts/test.sh` | Aucune commande unique et déterministe pour tester en environnement propre | Ajout de `check_env`, `compileall`, `pytest`, `pip check` et contrôle optionnel `--full` | `make test` | OK |
| `scripts/check_env.py` | Diagnostic insuffisant et absence de mode strict pour conditionner l'échec | Diagnostic core/full, sortie JSON et mode `--strict` pour signaler les défauts | `make doctor`, `make doctor-full` | Core OK, full imparfait sans Ollama/HF |
| `scripts/lock.sh` | Pas de lock hashé réellement versionné | Résolution avec `uv pip compile --generate-hashes` sur Python 3.11 | `make lock` puis `pip install -r requirements.lock` dans un venv neuf | OK |
| `scripts/prefetch_models.py` | Modèles HF téléchargés implicitement, sans contrôle explicite | Script d'opt-in qui lit les modèles du catalogue pour éviter les téléchargements dans les tests | Validation du script sans exécution de modèle massif | OK |
| `Makefile` | Les cibles nécessaires à la reproductibilité n'existaient pas | Ajout de `setup`, `test`, `doctor`, `doctor-full`, `models`, `lock` | `make setup`, `make test`, `make doctor` | OK |
| `.github/workflows/g0-ci.yml` | Le workflow ne réutilisait pas le lock et ne faisait pas de vérification explicite de dépendances | Installation depuis `requirements.lock`, `pip check`, puis `pytest -q tests` sur Python 3.11 | Validation du workflow sur la branche puis PR | Préparé ; exécution à valider après push |
| `tests/test_g0_config.py` | Aucun test sur la cohérence des dépendances, des modèles et du bootstrap | Ajout de contrats de version et de disponibilité de fichiers requis | `pytest -q tests/test_g0_config.py` | OK |
| `tests/test_extraction_smoke.py` | Pas de test de robustesse pour le PDF synthétique et les métadonnées | Ajout d'un test de granularité PDF + manifest | `pytest -q tests/test_extraction_smoke.py` | OK |
| `docs/SETUP_G0.md` | La procédure d'installation n'était pas décrite de façon exécutable | Documentation de l'installation, des commandes et des limites | Lecture du document et exécution des commandes | OK |
| `.devcontainer/devcontainer.json` | Le conteneur GitHub Codespaces ne forçait pas la version Python 3.11 | Ajout d'un devcontainer Python 3.11 avec bootstrap automatique | Vérification du JSON | OK |

## Contrôles réellement exécutés

- `git status --short --branch`
- `git log -5 --oneline`
- `git rev-parse HEAD`
- `git apply --check --verbose /tmp/.../g0_changes.patch`
- `make setup`
- `make doctor`
- `make test`
- `make doctor-full` (diagnostic externe, non strict dans l'exécution localisée)
- `make lock`
- `python3.11 -m venv /tmp/g0-lockcheck && /tmp/g0-lockcheck/bin/python -m pip install --requirement requirements.lock`
- `python -m pip check`
- `pytest -q tests`

## Résultats de validation

### Python et environnement
- Python de référence : `3.11.18`
- `.venv` créée avec `python3.11 -m venv .venv`
- `pip check` : aucune dépendance cassée
- `make doctor` : 22/22 OK
- `make test` : 6 tests passés, 0 échec, 0 ignoré

### Diagnostic externe (non bloquant pendant les tests standards)
- Tesseract : installé et disponible (`/usr/bin/tesseract`)
- Langues OCR : `fra` et `eng` présentes
- Ollama : non installé sur cette machine
- API Ollama locale : indisponible (connexion refusée sur `http://localhost:11434`)
- Modèles Hugging Face du catalogue : absents du cache local
- Ce diagnostic est volontairement non bloquant pour la suite standard de tests G0 ; il est signalé pour permettre la validation explicite d'un environnement complet.

### Lockfile
- `requirements.lock` généré via `uv pip compile --python-version 3.11 --generate-hashes`
- Installation dans un environnement neuf : OK
- `make lock` : OK
- `requirements.lock` versionné dans le dépôt : oui

## Limites et risques résiduels

- Le projet est validé sur Python 3.11. Les autres versions ne sont pas la cible de référence.
- Ollama et les modèles Hugging Face ne sont pas testés dans ce run local car ils sont externes et volumineux.
- Le workflow GitHub Actions doit être vérifié après push sur GitHub pour confirmer l’exécution réelle dans un runner Cloud.
- `make doctor-full --strict` échoue dans un environnement sans Ollama / modèles; c’est attendu et correspond à une détection de prérequis non satisfaits.
- Les vrais documents BRVM et le service Ollama ne sont pas utilisés dans les tests G0 standards, comme demandé.

## État final de G0

La préparation de G0 est terminée et validée localement dans Codespaces pour le plan de reproduction, l’environnement virtuel, le lockfile, le bootstrap, les tests et le diagnostic de configuration. Les contrôles de services externes restent des diagnostics séparés, sans dépendre des tests standards.
