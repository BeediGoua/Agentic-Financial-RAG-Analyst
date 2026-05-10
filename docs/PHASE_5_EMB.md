# PHASE 5 — Embeddings

## Objectif

Transformer les chunks texte en vecteurs numériques exploitables pour la recherche sémantique.

Entrée :


data/chunks/
Sortie :

data/embeddings/
Pourquoi cette étape est importante
Les LLM ne recherchent pas directement dans du texte brut.

Le retrieval moderne fonctionne avec :

texte
↓
vecteur numérique
↓
similarité vectorielle
↓
retrieval sémantique
Donc cette étape permet :

recherche sémantique ;
retrieval dense ;
hybrid retrieval ;
reranking futur ;
comparaison des stratégies.
Ce que nous faisons ici
Nous :

lisons les chunks ;
calculons les embeddings ;
stockons les vecteurs ;
conservons toutes les métadonnées ;
préparons la future vector database.
Important :

chunks = source de vérité
embeddings = artefacts calculés
vector DB = index de recherche
Architecture générale
chunks
↓
embedding model
↓
vecteurs
↓
stockage embeddings
↓
future vector DB
Pourquoi on stocke les embeddings
Nous ne voulons pas :

texte
↓
vector DB directement
Sinon :

impossible de réindexer facilement ;
difficile de comparer les modèles ;
difficile d’auditer ;
mauvaise reproductibilité.
Donc :

chunks persistés
↓
embeddings persistés
↓
vector DB reconstruisible
Modèles choisis
Nous utilisons deux modèles légers et réalistes.

1. MiniLM multilingual
Modèle :

sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
Avantages :

léger ;
rapide ;
multilingue ;
très bon baseline.
Limites :

moins performant sur retrieval complexe.
2. multilingual-e5-small
Modèle :

intfloat/multilingual-e5-small
Avantages :

excellent pour retrieval ;
très bon FR + EN ;
moderne ;
très utilisé pour RAG.
Limites :

un peu plus lent.
Pourquoi comparer plusieurs modèles
Nous ne savons pas encore :

quel modèle donnera le meilleur retrieval ;
quelle stratégie sera la plus robuste ;
quel compromis qualité/vitesse est optimal.
Donc nous produisons plusieurs jeux d’embeddings pour futures évaluations.

Architecture de la phase
data/chunks/
↓
ChunkEmbedder
↓
EmbeddingQuality
↓
EmbeddingSupervisor
↓
data/embeddings/
Structure du code
app/
  embeddings/
    __init__.py
    schemas.py
    models.py
    embedder.py
    quality.py
    supervisor.py
    run_embeddings.py
Rôle des fichiers
Fichier

Rôle

schemas.py

structure standard des embeddings

models.py

configuration des modèles

embedder.py

calcul embeddings

quality.py

validation qualité embeddings

supervisor.py

orchestration globale

run_embeddings.py

CLI de lancement

Structure des données
Input
data/chunks/
Exemple :

{
  "chunk_id": "section_orange_ci_2025_risk_001",
  "text": "...",
  "company": "ORANGE CI"
}
Output
data/embeddings/
Exemple :

{
  "chunk_id": "section_orange_ci_2025_risk_001",
  "embedding_model": "e5_small",
  "vector_dimension": 384,
  "embedding": [...],
  "company": "ORANGE CI"
}
Stratégies supportées
Nous générons des embeddings pour plusieurs stratégies de chunking :

recursive_fixed
page_aware
section_aware
Plus tard :

table_aware
semantic
markdown_aware
hierarchical
Structure de sortie
data/
  embeddings/
    recursive_fixed/
      mini_lm_multilingual/
      e5_small/

    page_aware/
      mini_lm_multilingual/
      e5_small/

    section_aware/
      mini_lm_multilingual/
      e5_small/

    quality/
Contrôles qualité
Nous vérifions :

nombre total d’embeddings ;
dimensions des vecteurs ;
erreurs ;
fichiers vides ;
cohérence des métadonnées.
Exemple :

{
  "status": "PASS",
  "total_records": 104,
  "dimensions": [384]
}
Ce que cette phase permet plus tard
Cette étape prépare :

PHASE 6 — Vector DB
embeddings
↓
Qdrant / Chroma / FAISS
Puis :

PHASE 7 — Retrieval
Comparaison :

dense retrieval ;
BM25 ;
hybrid retrieval.
Commandes
Lancer tous les embeddings
python -m app.embeddings.run_embeddings \
  --companies "ORANGE CI" \
  --years "2025"
Lancer seulement MiniLM
python -m app.embeddings.run_embeddings \
  --companies "ORANGE CI" \
  --years "2025" \
  --models "mini_lm_multilingual"
Lancer seulement E5
python -m app.embeddings.run_embeddings \
  --companies "ORANGE CI" \
  --years "2025" \
  --models "e5_small"
Forcer reconstruction
python -m app.embeddings.run_embeddings \
  --companies "ORANGE CI" \
  --years "2025" \
  --force
Ce que cette phase démontre
Cette phase montre :

compréhension retrieval dense ;
architecture RAG modulaire ;
comparaison expérimentale ;
traçabilité ;
préparation production.
Ce n’est pas juste :

texte → GPT
Nous construisons :

un système RAG évalué et reproductible
Résumé
Input
data/chunks/
Output
data/embeddings/
Modèles
MiniLM multilingual
multilingual-e5-small
Objectif
Préparer la future recherche sémantique et les comparaisons retrieval.