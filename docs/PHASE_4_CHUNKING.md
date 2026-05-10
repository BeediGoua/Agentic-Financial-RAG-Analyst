# PHASE 4 — CHUNKING MULTI-STRATÉGIES

## Objectif

Cette phase transforme les pages et tables nettoyées en chunks exploitables pour le futur système RAG.

Le chunking est une étape critique, car le retrieval travaillera directement sur ces chunks.

Un mauvais chunking entraîne :

mauvais chunks
↓
mauvais embeddings
↓
mauvais retrieval
↓
mauvaises citations
↓
mauvaises réponses RAG

---

## Entrées

data/processed/pages/
data/processed/tables/

---

## Sorties

data/chunks/

Sous-dossiers :

- recursive_fixed/
- page_aware/
- section_aware/
- table_aware/
- semantic/
- markdown_aware/
- hierarchical/
- quality/

---

## Stratégies implémentées

### 1. Recursive fixed

Baseline robuste.

Découpe le texte en respectant autant que possible :

- paragraphes ;
- lignes ;
- phrases ;
- mots.

C’est une meilleure baseline qu’un découpage fixe brutal.

---

### 2. Page-aware

Respecte les frontières de page.

Très utile pour :

- citations ;
- audit ;
- debugging retrieval.

---

### 3. Section-aware

Détecte des sections métier :

- risk ;
- debt ;
- revenue ;
- performance ;
- cash flow ;
- strategy ;
- governance ;
- dividend.

Objectif :

garder une cohérence métier dans les chunks.

---

### 4. Table-aware

Transforme les tables nettoyées en chunks spécialisés.

Très important pour les rapports financiers, car les valeurs numériques sont souvent dans les tableaux.

---

### 5. Semantic

Découpe selon les ruptures de sens entre phrases.

Utilise sentence-transformers si disponible.

Si le modèle n’est pas disponible, fallback vers recursive chunking.

---

### 6. Markdown-aware

Construit une structure pseudo-Markdown à partir des pages et découpe selon les titres détectés.

Utile quand le document contient des titres, listes ou blocs structurés.

---

### 7. Hierarchical

Crée deux niveaux :

- parent chunks ;
- child chunks.

Utile plus tard pour un retrieval parent-child.

---

## Schéma de chunk

Chaque chunk contient :

```json
{
  "chunk_id": "...",
  "chunking_strategy": "section_aware",
  "company": "ORANGE CI",
  "year": "2025",
  "document_type": "financial_statements",
  "source_pdf": "...",
  "source_url": "...",
  "page_start": 2,
  "page_end": 3,
  "section": "performance",
  "content_type": "text",
  "text": "..."
}

```

---

## Pourquoi comparer plusieurs stratégies ?

On ne sait pas encore quelle stratégie donnera le meilleur retrieval.

La comparaison se fera plus tard avec :

Recall@5 ;
MRR ;
Precision@5 ;
Citation accuracy ;
Answer faithfulness.
Stratégies recommandées pour MVP
À lancer par défaut :

recursive_fixed ;
page_aware ;
section_aware.
Ces trois stratégies donnent une comparaison simple et sérieuse.

Stratégies avancées
À tester ensuite :

table_aware ;
semantic ;
markdown_aware ;
hierarchical.
Elles permettent d’enrichir le benchmark et de montrer une vraie logique expérimentale.

## Commandes

### Stratégies principales :

```bash
python -m app.chunking.run_chunking --companies "ORANGE CI" --years "2025"
```

### Toutes les stratégies :

```bash
python -m app.chunking.run_chunking --companies "ORANGE CI" --years "2025" --all-strategies
```

### Stratégie spécifique :

```bash
python -m app.chunking.run_chunking --companies "ORANGE CI" --years "2025" --strategies "semantic"
```

---

## Rapport qualité

Chaque exécution produit :

```bash
data/chunks/quality/chunking_run_YYYYMMDD_HHMMSS.json
```

Le rapport contient :

```json
{
  "overall_status": "PASS",
  "strategies": [
    "recursive_fixed",
    "page_aware",
    "section_aware"
  ],
  "companies": [
    "ORANGE CI"
  ],
  "years": [
    "2025"
  ],
  "strategy_quality": {
    "recursive_fixed": {
      "status": "PASS",
      "total_outputs": 1,
      "success_outputs": 1,
      "errors": 0,
      "total_chunks": 12
    },
    "page_aware": {
      "status": "PASS",
      "total_outputs": 1,
      "success_outputs": 1,
      "errors": 0,
      "total_chunks": 15
    },
    "section_aware": {
      "status": "PASS",
      "total_outputs": 1,
      "success_outputs": 1,
      "errors": 0,
      "total_chunks": 15
    }
  },
  "strategy_results": {
    "recursive_fixed": [
      {
        "status": "success",
        "strategy": "recursive_fixed",
        "output_path": "data/chunks/recursive_fixed/financial_statements/2025/orange_ci/1.chunks.jsonl"
      }
    ],
    "page_aware": [
      {
        "status": "success",
        "strategy": "page_aware",
        "output_path": "data/chunks/page_aware/financial_statements/2025/orange_ci/1.chunks.jsonl"
      }
    ],
    "section_aware": [
      {
        "status": "success",
        "strategy": "section_aware",
        "output_path": "data/chunks/section_aware/financial_statements/2025/orange_ci/1.chunks.jsonl"
      }
    ]
  },
  "report_path": "data/chunks/quality/chunking_run_20250510_165018.json"
}
```