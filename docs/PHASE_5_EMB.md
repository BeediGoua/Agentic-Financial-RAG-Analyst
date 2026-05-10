
# PHASE 5 — Génération des Embeddings (Vecteurs)

##  Objectif et Flux
L'objectif est de transformer les chunks de texte produits à la Phase 4 en **vecteurs numériques** exploitables par les modèles d'intelligence artificielle pour la recherche sémantique.

- **Entrée** : `data/chunks/` (fichiers JSONL par stratégie)
- **Sortie** : `data/embeddings/` (fichiers JSONL avec vecteurs)

---

##  Pourquoi cette étape est-elle cruciale ?
Le "retrieval" moderne ne repose pas sur les mots-clés, mais sur la **proximité vectorielle** :
1. **Texte** ➔ **Vecteur numérique** (Embedding)
2. **Question utilisateur** ➔ **Vecteur numérique**
3. **Calcul de similarité** (Cosine Similarity) ➔ **Résultats sémantiques**

### La stratégie de Persistance
Contrairement à une injection directe en base de données, nous persistons les vecteurs sur disque pour :
- **Réindexation facile** sans recalculer les vecteurs (économie de temps/coût).
- **Auditabilité** : Possibilité d'inspecter les vecteurs et les métadonnées associées.
- **Comparabilité** : Tester différents modèles (MiniLM vs E5) sur les mêmes chunks.

---

## 🧠 Modèles de Langage Sélectionnés
Nous utilisons deux modèles complémentaires pour équilibrer vitesse et précision :

### 1. MiniLM Multilingual
- **Modèle** : `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Atouts** : Ultra-léger, rapide, supporte 50+ langues.
- **Usage** : Idéal pour les tests rapides et les baselines.

### 2. Multilingual E5 Small
- **Modèle** : `intfloat/multilingual-e5-small`
- **Atouts** : État de l'art pour le retrieval, optimisé pour les tâches de recherche.
- **Usage** : Recommandé pour la production et une précision sémantique maximale.

---

##  Architecture du Pipeline

### Organisation du Code (`app/embeddings/`)
| Fichier | Rôle |
| :--- | :--- |
| `schemas.py` | Définit la structure standard (`EmbeddingRecord`). |
| `models.py` | Configuration des modèles (noms, préfixes, dimensions). |
| `embedder.py` | Logique de calcul des embeddings et gestion du cache. |
| `quality.py` | Algorithmes de validation et d'audit. |
| `supervisor.py` | Orchestration multi-modèles et multi-stratégies. |
| `run_embeddings.py` | Interface en ligne de commande (CLI). |

### Hiérarchie de Stockage
Les vecteurs sont classés par **stratégie**, puis par **modèle** pour éviter tout conflit :
```text
data/embeddings/
├── recursive_fixed/
│   ├── mini_lm_multilingual/
│   └── e5_small/
├── page_aware/
│   └── ...
└── quality/ (Rapports d'audit horodatés)
```

---

##  Structure des Données (JSONL)

Chaque ligne de sortie conserve toutes les métadonnées sources pour une traçabilité totale :
```json
{
  "chunk_id": "page_aware_c9dc2c27...",
  "embedding_model": "mini_lm_multilingual",
  "vector_dimension": 384,
  "embedding": [0.012, -0.045, 0.088, ...],
  "source_pdf": "data/raw/reports/brvm/orange_ci/2025/...",
  "company": "ORANGE CI",
  "year": "2025",
  "text": "..."
}
```

---

##  Commandes Terminal (Usage)

### Tests ciblés (Strategies spécifiques)
```powershell
python -m app.embeddings.run_embeddings --companies "ORANGE CI" --years "2025" --models "mini_lm_multilingual" --strategies "page_aware,section_aware"
```

### Génération complète par modèle
```powershell
python -m app.embeddings.run_embeddings --companies "ORANGE CI" --years "2025" --models "mini_lm_multilingual"
```

### Mise à jour forcée (Recalcul total)
```powershell
python -m app.embeddings.run_embeddings --companies "ORANGE CI" --years "2025" --force
```

---

##  Audit et Contrôles Qualité
Le système génère un rapport JSON après chaque exécution. Nous vérifions :
- **Intégrité** : Aucun fichier vide ou corrompu.
- **Dimensions** : Tous les vecteurs d'un modèle doivent avoir la même taille (ex: 384).
- **Cohérence** : Le nombre d'embeddings doit correspondre au nombre de chunks sources.

> [!NOTE]
> Cette phase transforme une collection de documents en une **base de connaissances sémantique**, prête pour l'injection dans la Vector DB (Phase 6).

---
**Suivant :** [Phase 6 — Injection Vector DB](./PHASE_6_VECTORDB.md)