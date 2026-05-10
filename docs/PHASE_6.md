# PHASE 6 — Vector Database avec FAISS

## Objectif

La phase 6 transforme les embeddings produits à la phase 5 en index vectoriels exploitables pour la recherche sémantique.

Entrée :

```text
data/embeddings/
```

Sortie :

```text
data/vector_db/faiss/
```

À la fin de cette phase, le système ne génère pas encore de réponse avec un LLM.  
Il devient simplement capable de chercher rapidement les chunks les plus proches d’une future question utilisateur.

---

# Pourquoi cette phase existe

À la phase 5, nous avons produit des embeddings.

Un embedding est un vecteur numérique, par exemple :

```text
[0.12, -0.03, 0.44, ...]
```

Mais avoir des embeddings dans des fichiers JSONL ne suffit pas pour faire une recherche efficace.

Sans FAISS :

```text
question
↓
embedding question
↓
comparaison manuelle avec tous les vecteurs
↓
lent et peu scalable
```

Avec FAISS :

```text
question
↓
embedding question
↓
recherche top-k rapide
↓
chunks les plus proches
```

FAISS devient donc la couche d’indexation vectorielle du système.

---

# Rôle de FAISS

FAISS stocke et interroge les vecteurs.

Dans notre cas, il reçoit :

```text
embeddings des chunks
```

et il permettra plus tard de chercher :

```text
les chunks les plus similaires à une question
```

Nous utilisons :

```python
faiss.IndexFlatIP
```

Pourquoi ?

- simple ;
- local ;
- rapide ;
- adapté au MVP ;
- fonctionne bien avec des embeddings normalisés ;
- permet une similarité proche de la cosine similarity.

---

# Pourquoi FAISS ne suffit pas seul

FAISS ne stocke pas naturellement toute la richesse métier du chunk.

Il sait chercher des vecteurs, mais il ne suffit pas pour répondre à :

```text
Quelle entreprise ?
Quelle année ?
Quelle page ?
Quelle section ?
Quel texte ?
Quelle source ?
```

Donc, pour chaque index FAISS, nous stockons aussi :

```text
metadata.jsonl
```

Ce fichier garde les informations nécessaires pour reconstruire les citations et afficher les résultats.

---

# Sorties principales

Pour chaque couple :

```text
chunking_strategy + embedding_model
```

on produit :

```text
index.faiss
metadata.jsonl
```

Exemple :

```text
data/vector_db/faiss/
  recursive_fixed/
    mini_lm_multilingual/
      brvm/
        orange_ci/
          2025/
            financial_statements/
              index.faiss
              metadata.jsonl
```

---

# Ce que contient index.faiss

Le fichier :

```text
index.faiss
```

contient les vecteurs numériques indexés.

Il sert uniquement à la recherche vectorielle rapide.

---

# Ce que contient metadata.jsonl

Le fichier :

```text
metadata.jsonl
```

contient les informations alignées avec les vecteurs FAISS.

Exemple :

```json
{
  "vector_id": 12,
  "chunk_id": "recursive_fixed_abc123",
  "chunking_strategy": "recursive_fixed",
  "embedding_model": "mini_lm_multilingual",
  "company": "ORANGE CI",
  "year": "2025",
  "document_type": "financial_statements",
  "page_start": 2,
  "page_end": 2,
  "section": "performance",
  "text": "Le chiffre d'affaires consolidé..."
}
```

Le champ important est :

```text
vector_id
```

Il correspond à la position du vecteur dans FAISS.

Donc quand FAISS retourne :

```text
vector_id = 12
```

on va chercher la ligne correspondante dans :

```text
metadata.jsonl
```

et on récupère le texte + les métadonnées.

---

# Structure du code

```text
app/
  vector_db/
    __init__.py
    schemas.py
    faiss_index.py
    quality.py
    supervisor.py
    run_indexing.py
```

---

# Détail des fichiers importants

## 1. schemas.py

Rôle :

```text
définir les structures de données de la phase vector DB
```

Ce fichier contient principalement :

```python
VectorMetadata
IndexingResult
```

---

## VectorMetadata

Cette classe décrit une ligne de metadata associée à un vecteur FAISS.

Elle contient :

```text
vector_id
chunk_id
chunking_strategy
embedding_model
source_pdf
company
year
document_type
page_start
page_end
section
content_type
text
```

Pourquoi c’est important :

FAISS stocke les vecteurs, mais pas les informations métier.  
`VectorMetadata` garantit que chaque vecteur reste relié à son chunk d’origine.

Sans ce fichier, on pourrait retrouver un vecteur proche, mais pas savoir :

- d’où il vient ;
- quel texte il représente ;
- quelle page citer ;
- quelle entreprise concerne le chunk.

---

## IndexingResult

Cette classe décrit le résultat d’une indexation.

Elle garde :

```text
status
strategy
model
input_path
index_path
metadata_path
vectors_count
vector_dimension
error
```

Pourquoi c’est utile :

Elle permet de suivre proprement :

- quels fichiers ont été indexés ;
- combien de vecteurs ont été ajoutés ;
- s’il y a eu une erreur ;
- où sont les fichiers créés.

---

# 2. faiss_index.py

C’est le fichier le plus important de la phase 6.

Rôle :

```text
construire les index FAISS à partir des embeddings JSONL
```

Il contient :

```python
FaissIndexBuilder
```

---

## FaissIndexBuilder

Ce composant fait 5 choses principales.

---

## Étape 1 — Découvrir les embeddings disponibles

Méthode :

```python
discover_embedding_files()
```

Elle cherche automatiquement :

```text
*.embeddings.jsonl
```

dans :

```text
data/embeddings/
```

Exemple détecté :

```text
data/embeddings/recursive_fixed/mini_lm_multilingual/...
```

Pourquoi c’est important :

Tu n’as pas besoin de coder chaque stratégie à la main.

Si plus tard tu génères :

```text
semantic
markdown_aware
table_aware
e5_small
```

la phase 6 peut les détecter automatiquement.

---

## Étape 2 — Identifier la stratégie et le modèle

Méthode :

```python
infer_strategy_model()
```

Elle lit le chemin du fichier pour récupérer :

```text
strategy
model
```

Exemple :

```text
data/embeddings/page_aware/mini_lm_multilingual/...
```

donne :

```text
strategy = page_aware
model = mini_lm_multilingual
```

Pourquoi c’est important :

Cela permet de créer un index séparé pour chaque combinaison.

---

## Étape 3 — Charger les embeddings

Méthode :

```python
load_jsonl()
```

Elle lit chaque ligne du fichier `.embeddings.jsonl`.

Chaque ligne contient :

- chunk_id ;
- texte ;
- metadata ;
- embedding.

---

## Étape 4 — Construire la matrice numpy

Dans :

```python
build_index_for_file()
```

les embeddings sont transformés en matrice :

```python
np.array(vectors, dtype="float32")
```

FAISS attend des vecteurs en `float32`.

Si les vecteurs ont une mauvaise forme, le code renvoie une erreur.

---

## Étape 5 — Créer l’index FAISS

Toujours dans :

```python
build_index_for_file()
```

on crée :

```python
index = faiss.IndexFlatIP(vector_dimension)
index.add(matrix)
```

Cela ajoute tous les vecteurs dans l’index.

Ensuite on sauvegarde :

```python
faiss.write_index(index, str(index_path))
```

---

## Étape 6 — Sauvegarder metadata.jsonl

En parallèle, on écrit :

```text
metadata.jsonl
```

avec les métadonnées alignées aux vecteurs.

C’est essentiel pour la phase retrieval.

---

# 3. quality.py

Rôle :

```text
vérifier que l’indexation s’est bien passée
```

Ce fichier contient :

```python
VectorDBQuality
```

---

## VectorDBQuality

Il analyse les résultats de FAISS indexing.

Il vérifie :

```text
nombre de fichiers traités
nombre de succès
nombre de fichiers vides
nombre d’erreurs
nombre total de vecteurs
dimensions des vecteurs
couples stratégie/modèle indexés
```

Exemple de sortie :

```json
{
  "status": "PASS",
  "total_files": 5,
  "success_files": 5,
  "empty_files": 0,
  "error_files": 0,
  "total_vectors": 37,
  "dimensions": [384],
  "indexed_pairs": [
    "recursive_fixed::mini_lm_multilingual"
  ]
}
```

---

## Pourquoi c’est important

Avant de passer au retrieval, il faut savoir :

- si l’index existe ;
- s’il contient bien des vecteurs ;
- si les dimensions sont cohérentes ;
- si tous les modèles attendus ont été indexés.

Sans cette validation, on pourrait commencer la phase retrieval sur un index vide ou cassé.

---

# 4. supervisor.py

Rôle :

```text
orchestrer toute la phase 6
```

Ce fichier contient :

```python
VectorDBSupervisor
```

---

## VectorDBSupervisor

Il fait :

```text
lancement de l’indexation
↓
contrôle qualité
↓
rapport final
```

Il appelle :

```python
FaissIndexBuilder
```

puis :

```python
VectorDBQuality
```

Ensuite il produit un rapport JSON dans :

```text
data/vector_db/faiss/quality/
```

---

## Pourquoi ce fichier est important

Comme dans les autres phases, le supervisor centralise :

- l’exécution ;
- les erreurs ;
- les résultats ;
- le rapport qualité ;
- le statut global.

Cela garde le même pattern architectural que les phases précédentes.

---

# 5. run_indexing.py

Rôle :

```text
point d’entrée CLI de la phase 6
```

C’est le fichier que tu exécutes dans le terminal.

Exemple :

```bash
python -m app.vector_db.run_indexing
```

---

## Ce qu’il fait

Il lit les arguments :

```text
--strategies
--models
--force
```

Puis il lance :

```python
VectorDBSupervisor
```

---

## Commandes utiles

Indexer tout ce qui existe :

```bash
python -m app.vector_db.run_indexing
```

Indexer seulement MiniLM :

```bash
python -m app.vector_db.run_indexing --models "mini_lm_multilingual"
```

Indexer seulement certaines stratégies :

```bash
python -m app.vector_db.run_indexing --strategies "recursive_fixed,page_aware,section_aware"
```

Forcer reconstruction :

```bash
python -m app.vector_db.run_indexing --force
```

---

# Pourquoi les index sont séparés par stratégie et modèle

Nous voulons comparer plus tard :

```text
chunking strategy
+
embedding model
+
retrieval quality
```

Donc il faut garder des index séparés.

Exemple :

```text
recursive_fixed + mini_lm_multilingual
page_aware + mini_lm_multilingual
section_aware + mini_lm_multilingual
recursive_fixed + e5_small
```

Chaque combinaison aura son propre index FAISS.

Cela permet de comparer proprement :

- Recall@5 ;
- MRR ;
- Precision@5 ;
- citation accuracy.

---

# Pourquoi ne pas tout mettre dans un seul index

Mauvaise idée au début.

Si on mélange :

```text
recursive_fixed
page_aware
section_aware
```

dans le même index, on ne peut plus comparer proprement les stratégies.

Donc pour le benchmark :

```text
1 stratégie + 1 modèle = 1 index
```

C’est beaucoup plus rigoureux.

---

# Ce que cette phase produit réellement

À la fin, tu obtiens :

```text
data/vector_db/faiss/
  recursive_fixed/
    mini_lm_multilingual/
      ...
        index.faiss
        metadata.jsonl

  page_aware/
    mini_lm_multilingual/
      ...
        index.faiss
        metadata.jsonl

  section_aware/
    mini_lm_multilingual/
      ...
        index.faiss
        metadata.jsonl

  quality/
    vector_db_run_YYYYMMDD_HHMMSS.json
```

---

# Lien avec la phase suivante

La phase 7 sera :

```text
Retrieval
```

Elle utilisera :

```text
index.faiss
metadata.jsonl
```

pour faire :

```text
question utilisateur
↓
embedding de la question
↓
recherche FAISS
↓
top-k vector_ids
↓
récupération metadata
↓
chunks pertinents
```

---

# Exemple concret

Question future :

```text
Quels sont les résultats financiers d’Orange CI en 2025 ?
```

Pipeline retrieval :

```text
question
↓
embedding question
↓
FAISS search
↓
top 5 vector_ids
↓
metadata.jsonl
↓
text + page + source
```

Résultat attendu :

```json
{
  "chunk_id": "page_aware_abc123",
  "score": 0.82,
  "company": "ORANGE CI",
  "year": "2025",
  "page_start": 2,
  "text": "Le chiffre d'affaires consolidé..."
}
```

---

# Ce qu’on ne fait pas encore

À cette phase, on ne fait pas encore :

- génération LLM ;
- réponse finale ;
- citations formatées ;
- évaluation RAG ;
- reranking.

On construit uniquement la couche :

```text
indexation vectorielle
```

---

# Validation de la phase 6

La phase 6 est validée si :

```text
overall_status = PASS
total_vectors > 0
dimensions cohérentes
index.faiss créé
metadata.jsonl créé
```

---

# Résumé

## Input

```text
data/embeddings/
```

## Output

```text
data/vector_db/faiss/
```

## Fichiers clés

```text
faiss_index.py  = construit les index
metadata.jsonl  = garde le lien chunk ↔ texte ↔ citations
index.faiss     = recherche vectorielle
quality.py      = vérifie indexation
supervisor.py   = orchestre
run_indexing.py = lance la phase
```

## Objectif final

Préparer la phase Retrieval en gardant une architecture :

```text
traçable
modulaire
comparable
évaluable
```
