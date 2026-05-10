# PHASE 8 — Reranking

## Objectif

La phase 8 améliore l’ordre des chunks récupérés par la phase Retrieval.

Le retrieval récupère un ensemble de chunks candidats.

Le reranking réévalue ces chunks plus finement par rapport à la question utilisateur.

Pipeline :

```text
question
↓
retrieval top-k ou top-n
↓
reranking
↓
top-k final mieux ordonné
```

Cette phase ne génère pas encore de réponse finale avec un LLM.

Elle sert à améliorer la qualité du contexte qui sera donné au futur générateur.

---

# Pourquoi le reranking est important

Le retrieval dense, BM25 ou hybrid peut récupérer les bons passages, mais pas toujours dans le bon ordre.

Exemple :

```text
Top 1 retrieval : passage moyennement utile
Top 2 retrieval : passage très pertinent
Top 3 retrieval : passage bruité
```

Le reranker va relire chaque paire :

```text
question + chunk
```

et donner un score de pertinence plus précis.

Résultat :

```text
Top 1 reranking : passage très pertinent
Top 2 reranking : passage moyennement utile
Top 3 reranking : passage bruité
```

Cela améliore fortement :

- la qualité du contexte ;
- les citations ;
- la génération future ;
- la réduction des hallucinations.

---

# Différence entre retrieval et reranking

## Retrieval

Le retrieval cherche dans toute la base.

Il doit être rapide.

Méthodes :

- dense retrieval ;
- BM25 ;
- hybrid retrieval.

## Reranking

Le reranking ne cherche pas dans toute la base.

Il prend seulement les candidats récupérés.

Il les réordonne avec un modèle plus précis.

```text
retrieval = trouver les candidats
reranking = mieux classer les candidats
```

---

# Modèles utilisés

## mini_cross_encoder

Modèle :

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

Rôle :

- modèle principal léger ;
- bon compromis qualité/vitesse ;
- adapté au MVP.

## tiny_cross_encoder

Modèle :

```text
cross-encoder/ms-marco-TinyBERT-L-2-v2
```

Rôle :

- modèle très léger ;
- plus rapide ;
- qualité souvent plus faible ;
- utile pour tests rapides.

---

# Structure du code

```text
app/
  reranking/
    __init__.py
    schemas.py
    models.py
    cross_encoder.py
    quality.py
    supervisor.py
    run_reranking.py
```

---

# Rôle des fichiers

| Fichier | Rôle |
|---|---|
| schemas.py | définit la structure des résultats rerankés |
| models.py | centralise les modèles disponibles |
| cross_encoder.py | applique le modèle de reranking |
| quality.py | vérifie que le reranking produit bien des résultats |
| supervisor.py | orchestre toute la phase |
| run_reranking.py | point d’entrée CLI |

---

# Fichier important : schemas.py

Ce fichier définit :

```text
RerankedResult
RerankingRun
```

## RerankedResult

Chaque résultat reranké contient :

- nouveau rang ;
- ancien rang retrieval ;
- score retrieval ;
- score reranking ;
- score final ;
- méthode retrieval ;
- modèle reranking ;
- chunk_id ;
- metadata ;
- texte.

Exemple :

```json
{
  "rank": 1,
  "original_rank": 4,
  "retrieval_score": 0.71,
  "reranking_score": 6.42,
  "final_score": 6.42,
  "retrieval_method": "hybrid",
  "reranking_model": "mini_cross_encoder",
  "chunk_id": "...",
  "company": "ORANGE CI",
  "year": "2025",
  "page_start": 2,
  "section": "performance",
  "text": "..."
}
```

Ce format est important pour comparer :

```text
avant reranking
vs
après reranking
```

---

# Fichier important : models.py

Ce fichier contient les modèles disponibles.

Avantage :

- éviter de mettre les noms Hugging Face partout ;
- changer facilement de modèle ;
- ajouter plus tard BGE reranker ou Cohere rerank.

Exemple :

```python
RERANKING_MODELS = {
    "mini_cross_encoder": {
        "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2"
    }
}
```

---

# Fichier important : cross_encoder.py

C’est le cœur de la phase 8.

Il contient :

```text
CrossEncoderReranker
```

Rôle :

1. lire un fichier retrieval_run ;
2. récupérer la question ;
3. récupérer les chunks candidats ;
4. créer des paires question/chunk ;
5. scorer chaque paire ;
6. trier les chunks ;
7. retourner le top-k final.

Le modèle reçoit :

```text
(question, chunk_text)
```

et retourne un score de pertinence.

---

# Fichier important : quality.py

Ce fichier vérifie que la phase fonctionne correctement.

Il mesure :

- nombre de runs ;
- nombre de succès ;
- runs vides ;
- erreurs ;
- nombre total de résultats rerankés.

Il produit :

```text
PASS
WARNING
FAIL
```

Cette validation évite de passer à la génération avec un reranking vide.

---

# Fichier important : supervisor.py

Le supervisor orchestre :

```text
retrieval_run
↓
reranker
↓
quality
↓
report
```

Il sauvegarde un rapport dans :

```text
data/reranking/runs/
```

---

# Fichier important : run_reranking.py

C’est le point d’entrée CLI.

Commandes principales :

```bash
python -m app.reranking.run_reranking
```

Par défaut, il prend le dernier fichier :

```text
data/retrieval/runs/retrieval_run_*.json
```

Tu peux aussi préciser un fichier :

```bash
python -m app.reranking.run_reranking --retrieval-run "data/retrieval/runs/retrieval_run_YYYYMMDD_HHMMSS.json"
```

---

# Entrées

La phase lit :

```text
data/retrieval/runs/retrieval_run_*.json
```

Ces fichiers viennent de la phase 7.

---

# Sorties

La phase produit :

```text
data/reranking/runs/reranking_run_YYYYMMDD_HHMMSS.json
```

---

# Exemple de sortie

```json
{
  "overall_status": "PASS",
  "retrieval_run_path": "data/retrieval/runs/retrieval_run_20260510_201000.json",
  "reranking_model": "mini_cross_encoder",
  "top_k": 5,
  "runs": [
    {
      "retrieval_method": "hybrid",
      "chunking_strategy": "section_aware",
      "embedding_model": "mini_lm_multilingual",
      "reranked_results_count": 5
    }
  ]
}
```

---

# Comment tester

## 1. Lancer un retrieval

```bash
python -m app.retrieval.run_retrieval --query "Quels sont les résultats financiers d'Orange CI en 2025 ?" --companies "ORANGE CI" --years "2025"
```

## 2. Lancer le reranking

```bash
python -m app.reranking.run_reranking
```

## 3. Tester un modèle plus léger

```bash
python -m app.reranking.run_reranking --model "tiny_cross_encoder"
```

---

# Ce qu’on ne fait pas encore

À cette phase :

- pas de génération LLM ;
- pas de réponse finale ;
- pas de citations formatées ;
- pas d’évaluation complète.

On améliore seulement l’ordre des chunks.

---

# Lien avec la phase suivante

La phase suivante sera :

```text
PHASE 9 — Generation contrôlée
```

Elle utilisera :

```text
top chunks rerankés
```

pour produire une réponse :

- concise ;
- sourcée ;
- avec citations ;
- sans hallucination volontaire.

---

# Résumé

La phase 8 transforme :

```text
retrieval candidates
```

en :

```text
ranked evidence
```

C’est une étape clé entre :

```text
retrieval
```

et :

```text
generation
```

Elle rend le futur RAG plus fiable, plus précis et plus défendable.