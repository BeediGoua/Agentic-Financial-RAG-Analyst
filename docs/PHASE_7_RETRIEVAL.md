# PHASE 7 — Retrieval

## Objectif

La phase 7 construit la couche de recherche du système RAG.

Elle permet de retrouver les chunks les plus pertinents à partir d’une question utilisateur.

Entrées :

```text
data/chunks/
data/vector_db/faiss/
```

Sorties :

```text
data/retrieval/runs/
```

Cette phase ne génère pas encore de réponse finale avec un LLM.

Elle sert uniquement à retrouver les meilleurs passages sources.

---

# Pourquoi cette phase est critique

Dans un système RAG, le LLM ne peut répondre correctement que si les bons contextes sont récupérés.

Mauvais retrieval :

```text
mauvais chunks récupérés
↓
mauvais contexte
↓
mauvaise réponse
↓
hallucinations
```

Bon retrieval :

```text
question
↓
bons passages
↓
réponse sourcée possible
```

Le retrieval est donc un composant central du système.

---

# Méthodes implémentées

## 1. Dense retrieval

Utilise :

```text
embedding question
+
FAISS search
```

Avantages :

- recherche sémantique ;
- retrouve des passages même si les mots ne sont pas identiques ;
- utile pour questions naturelles.

Limites :

- peut rater les termes financiers exacts ;
- dépend fortement du modèle d’embedding.

---

## 2. BM25 retrieval

Utilise :

```text
recherche lexicale
```

Avantages :

- excellent pour termes exacts ;
- utile pour EBITDA, IFRS, dette, dividende ;
- simple et rapide.

Limites :

- ne comprend pas vraiment le sens ;
- sensible aux formulations.

---

## 3. Hybrid retrieval

Combine :

```text
dense retrieval
+
BM25
```

Objectif :

- profiter de la sémantique ;
- garder la précision lexicale ;
- améliorer la robustesse.

C’est souvent la meilleure approche pour les systèmes RAG financiers.

---

# Architecture de la phase

```text
question
↓
DenseRetriever / BM25Retriever / HybridRetriever
↓
top-k chunks
↓
scores + metadata
↓
rapport retrieval
```

---

# Structure du code

```text
app/
  retrieval/
    __init__.py
    schemas.py
    dense.py
    bm25.py
    hybrid.py
    quality.py
    supervisor.py
    run_retrieval.py
```

---

# Rôle des fichiers

| Fichier | Rôle |
|---|---|
| schemas.py | structure des résultats retrieval |
| dense.py | recherche vectorielle FAISS |
| bm25.py | recherche lexicale BM25 |
| hybrid.py | fusion dense + BM25 |
| quality.py | validation des runs retrieval |
| supervisor.py | orchestration des méthodes |
| run_retrieval.py | CLI pour tester des requêtes |

---

# Résultat retourné

Chaque résultat contient :

```json
{
  "rank": 1,
  "score": 0.82,
  "retrieval_method": "hybrid",
  "chunk_id": "...",
  "company": "ORANGE CI",
  "year": "2025",
  "page_start": 2,
  "page_end": 2,
  "section": "performance",
  "text": "..."
}
```

---

# Pourquoi conserver les metadata

Les metadata permettent :

- citations ;
- filtrage entreprise ;
- filtrage année ;
- comparaison stratégies ;
- audit retrieval ;
- future génération sourcée.

---

# Commandes

## Test complet

```bash
python -m app.retrieval.run_retrieval --query "Quels sont les résultats financiers d'Orange CI en 2025 ?" --methods "hybrid" --strategies "section_aware" --models "mini_lm_multilingual" --companies "ORANGE CI" --years "2025"
```

## Dense seulement

```bash
python -m app.retrieval.run_retrieval --query "chiffre d'affaires Orange CI 2025" --methods "dense" --strategies "section_aware" --models "mini_lm_multilingual" --companies "ORANGE CI" --years "2025"
```

## Hybrid seulement

```bash
python -m app.retrieval.run_retrieval --query "résultat net chiffre d'affaires EBITDA Orange CI 2025" --methods "hybrid" --strategies "section_aware" --models "mini_lm_multilingual" --companies "ORANGE CI" --years "2025"
```

---

# Ce que cette phase permet de comparer

Nous pouvons maintenant comparer :

- dense vs BM25 vs hybrid ;
- recursive_fixed vs page_aware vs section_aware ;
- MiniLM vs E5-small ;
- qualité des passages récupérés.

---

# Ce qu’on ne fait pas encore

À cette phase :

- pas de génération LLM ;
- pas de réponse finale ;
- pas de RAG complet ;
- pas de reranking avancé.

La phase suivante sera :

```text
PHASE 8 — Retrieval Evaluation
```

ou :

```text
PHASE 8 — Reranking
```

selon l’ordre choisi.

---

# Validation

La phase 7 est validée si :

- les requêtes retournent des résultats ;
- les scores sont cohérents ;
- les metadata sont présentes ;
- les passages récupérés semblent utiles ;
- les rapports sont sauvegardés.

---

# Résumé

Cette phase transforme le projet en moteur de recherche documentaire.

Le pipeline devient :

```text
question
↓
retrieval
↓
chunks pertinents
↓
future réponse sourcée
```

C’est la première vraie brique fonctionnelle du RAG.