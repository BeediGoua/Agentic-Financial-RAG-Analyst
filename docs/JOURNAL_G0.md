# Journal technique — G0 : environnement reproductible

Date : 17 novembre 2026

Dépôt : `BeediGoua/Agentic-Financial-RAG-Analyst`

Branche : `chore/g0-reproducible-env-20261117`

Base de référence : `a869755cc88c132f69a93aae7593d8e20413937e`

## Corrections et vérifications

| Fichier | Problème | Correction / raison | Vérification |
| --- | --- | --- | --- |
| `requirements.txt`, `requirements-dev.txt`, `requirements.lock` | Dépendances non figées et dépendances redondantes | Versions directes exactes, lock transitif généré avec hashes pour Python 3.11; retrait de ChromaDB non utilisé | Installations `.venv` et environnement neuf; `pip check` réussi |
| `scripts/bootstrap.sh` | Une `.venv` existante avec Python incompatible pouvait être réutilisée | Bootstrap limité à Python 3.11; vérification de l'interpréteur de `.venv` avant toute installation, erreur explicite sinon | `make setup`; test négatif `.venv` simulée en 3.12 rejetée |
| `scripts/check_env.py`, `Makefile` | Doctor core ne validait pas OCR; doctor-full n'inspectait que deux modèles HF | Core exige Tesseract et `fra`/`eng`; full vérifie Ollama/API/modèle/digest et les quatre modèles HF sans téléchargement | `make doctor`; sortie JSON de `doctor-full` liste chaque composant et les quatre modèles absents |
| Catalogues de modèles, `embedder.py`, `cross_encoder.py`, `prefetch_models.py` | Les noms HF pointaient sur des révisions mouvantes | Ajout des révisions exactes et leur passage aux loaders et au préchargement | Test des quatre identifiants/révisions; aucun poids téléchargé pour ces contrôles |
| `.env.example` | Aucun moyen de contrôler le digest Ollama | Ajout de `OLLAMA_MODEL_DIGEST`, optionnel; doctor compare la valeur attendue au digest API | Contrôle du code et diagnostic local; Ollama non disponible |
| `.github/workflows/g0-ci.yml` | La CI installait hors du parcours réel `make setup` | CI installe Tesseract puis exécute `make setup`, `make doctor`, `make test`; inventaire depuis `.venv` | Run push 44081652672 : chaque étape réussie, 8 tests passés |
| `.devcontainer/devcontainer.json` | Codespaces ne garantissait pas les prérequis OCR | Installation de Tesseract + langues avant `make setup` | JSON vérifié; setup Codespaces réel déjà exécuté dans la session |
| `docs/SETUP_G0.md` | Les consignes ne distinguaient pas tests obligatoires et dépendances d'inférence | Procédures distinctes, téléchargement explicite, révisions HF et contrôle du digest Ollama | Relecture des instructions et contrôles sans téléchargement |

## Résultats réels

- Python : `3.11.18`; `.venv` isolée.
- `make setup` : réussi.
- `make doctor` : réussi, Python/dépendances/Tesseract/langues contrôlés.
- `make test` : **8 tests passés, 0 échoué, 0 ignoré**.
- Test de non-régression : bootstrap refuse une `.venv` simulée Python 3.12
  avant d'installer quoi que ce soit.
- Environnement neuf depuis `requirements.lock` : installation réussie,
  `pip check` sans dépendance cassée, 8 tests passés (second environnement
  Python 3.11 créé après les dernières corrections).
- Tesseract : installé, langues `fra` et `eng` disponibles.
- Ollama : absent; API locale non joignable; `qwen2.5:7b` et son digest n'ont
  donc pas pu être vérifiés ni exécutés.
- Hugging Face : les quatre révisions ont été consultées depuis les seules
  métadonnées des dépôts. Les quatre modèles ne sont pas en cache local et
  n'ont pas été téléchargés ni exécutés.
- Révisions HF verrouillées :
  - `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` :
    `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`
  - `intfloat/multilingual-e5-small` :
    `614241f622f53c4eeff9890bdc4f31cfecc418b3`
  - `cross-encoder/ms-marco-MiniLM-L-6-v2` :
    `233902d25c440f23af6f7d6e94d2946bac0bee0a`
  - `cross-encoder/ms-marco-TinyBERT-L-2-v2` :
    `81d1926f67cb8eee2c2be17ca9f793c7c3bd20cc`
- GitHub Actions : run push `44081652672`, commit
  `e4174c05a879937a6b228d91b68698209b4e1356`, **success**. Les trois parcours
  réels `make setup`, `make doctor`, `make test` ont réussi; le log CI confirme
  8 tests passés, `doctor` 25/25 et `pip check` sans dépendance cassée.
  Le run pull request `44081660701` sur le même commit est également **success**
  et confirme les mêmes résultats.
  URL push : `https://github.com/BeediGoua/Agentic-Financial-RAG-Analyst/actions/runs/44081652672`.
  URL PR : `https://github.com/BeediGoua/Agentic-Financial-RAG-Analyst/actions/runs/44081660701`.
- La mise à jour documentaire `a10977396d92255c66de4f5192af8137dd446355`
  a également passé le run push `44082704087` et le run PR `44082711544`.

## Limites / séparation des niveaux

G0 obligatoire = Python 3.11, lock Python, environnement isolé, Tesseract avec
`fra`/`eng`, `make setup`, `make doctor`, `make test` et `pip check`. Il ne
dépend pas de données BRVM, d'Ollama ni de poids de modèles.

Le run CI cité porte sur le commit de code G0; ce journal ne modifie pas le
comportement du workflow. Le commit de journalisation déclenche une nouvelle CI.

Les contrôles Ollama/HF de `doctor-full` sont diagnostics facultatifs. Un
échec strict en leur absence est attendu. Aucune inférence complète n'est
déclarée testée. Le lock Python ne couvre pas les paquets système ni les poids
de modèles; les quatre révisions HF sont épinglées, et le digest Ollama reste
à renseigner après téléchargement explicite.
