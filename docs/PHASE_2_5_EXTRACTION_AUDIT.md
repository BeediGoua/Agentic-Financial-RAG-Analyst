# PHASE 2.5 — AUDIT QUALITÉ DE L'EXTRACTION

## Objectif

Cette sous-étape vérifie que les sorties de la phase 2 sont suffisamment fiables avant de passer au nettoyage, au chunking, aux embeddings et au RAG.

Le but n'est pas encore d'évaluer un modèle RAG.

Le but est de vérifier la qualité des données extraites depuis les PDF.

---

## Pourquoi cette étape est importante

Dans un système RAG documentaire, la qualité finale dépend fortement de la qualité du texte extrait.

Une mauvaise extraction entraîne :

mauvaise extraction PDF
↓
mauvais nettoyage
↓
mauvais chunking
↓
mauvais retrieval
↓
réponses incorrectes ou hallucinations

Cette étape sert donc de barrière qualité entre :

- les PDF bruts ;
- les données exploitables.

---

## Ce que l'on vérifie

### Texte extrait

On contrôle :

- nombre total de pages ;
- pages vides ;
- pages de faible qualité ;
- pages passées par OCR ;
- exemples de texte extrait.

### Tables extraites

On contrôle :

- nombre total de tables ;
- nombre moyen de lignes ;
- nombre moyen de colonnes ;
- exemples de tables extraites.

### Métadonnées

On vérifie indirectement que les sorties conservent :

- company ;
- year ;
- document_type ;
- source_pdf ;
- page_number.

---

## Agents utilisés

### ExtractionAuditAgent

Fichier :

app/extraction/extraction_audit.py

Rôle :

- lire les fichiers `.pages.jsonl` ;
- lire les fichiers `.tables.jsonl` ;
- calculer des métriques simples ;
- générer un rapport d'audit ;
- donner une décision : PASS, WARNING ou FAIL.

---

## Entrées

L'audit lit les sorties de la phase 2 :

data/extracted/pages/
data/extracted/tables/

---

## Sorties

L'audit produit :

data/extracted/quality/latest_extraction_audit.json

---

## Règles de décision

### PASS

On peut passer à l'étape suivante si :

- des pages ont bien été extraites ;
- le taux de pages vides est faible ;
- le taux de pages faible qualité est acceptable ;
- les métadonnées sont présentes ;
- les tables sont détectées quand les documents en contiennent.

### WARNING

On doit vérifier manuellement si :

- certaines pages sont faibles ;
- peu de tables sont extraites ;
- OCR est beaucoup utilisé ;
- les exemples semblent partiellement cassés.

### FAIL

On ne doit pas continuer si :

- aucune page n'est extraite ;
- beaucoup de pages sont vides ;
- l'extraction échoue sur plusieurs documents ;
- les métadonnées sont absentes.

---

## Commande

Exemple :

```bash
python -m app.extraction.extraction_audit --companies "ORANGE CI" --years "2025"