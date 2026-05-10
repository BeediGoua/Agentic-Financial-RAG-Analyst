# PHASE 3 — NETTOYAGE + METADATA ENRICHMENT

## Objectif

Cette phase transforme les données extraites en données propres, cohérentes et exploitables pour les futures étapes RAG.

Entrées :

- pages extraites ;
- tables extraites ;
- métadonnées extraction.

Sorties :

- pages nettoyées ;
- tables nettoyées ;
- métadonnées normalisées ;
- rapport qualité processing.

Cette phase ne fait PAS encore :

- chunking ;
- embeddings ;
- vector database ;
- retrieval ;
- génération LLM.

---

# Architecture de la phase

Extracted Pages + Tables
↓
TextCleaningAgent
↓
TableCleaningAgent
↓
MetadataEnrichmentAgent
↓
ProcessingQualityAgent
↓
Processed structured data

---

# Pourquoi cette phase est importante

L’extraction brute contient souvent :

- espaces multiples ;
- caractères invisibles ;
- lignes vides ;
- cellules incohérentes ;
- métadonnées incomplètes ;
- texte mal normalisé.

Si ces problèmes ne sont pas corrigés :

mauvais nettoyage
↓
mauvais chunking
↓
mauvais embeddings
↓
mauvais retrieval
↓
mauvaises réponses RAG

Cette phase prépare donc le terrain pour :

- chunking métier ;
- embeddings ;
- retrieval ;
- citations fiables ;
- évaluation RAG.

---

# Structure des dossiers

data/
processed/
pages/
tables/
quality/

---

# Agents utilisés

## TextCleaningAgent

Fichier :

app/processing/text_cleaning_agent.py

Rôle :

- nettoyer les pages extraites ;
- supprimer les caractères parasites ;
- normaliser espaces et retours ligne ;
- conserver les métadonnées.

Entrée :

.pages.jsonl

Sortie :

.clean_pages.jsonl

---

## TableCleaningAgent

Fichier :

app/processing/table_cleaning_agent.py

Rôle :

- nettoyer les cellules des tableaux ;
- supprimer les lignes entièrement vides ;
- normaliser les valeurs texte ;
- conserver les métadonnées financières.

Entrée :

.tables.jsonl

Sortie :

.clean_tables.jsonl

---

## MetadataEnrichmentAgent

Fichier :

app/processing/metadata_enrichment_agent.py

Rôle :

- vérifier les métadonnées obligatoires ;
- mesurer la complétude metadata ;
- détecter les champs manquants.

Métadonnées critiques :

- company ;
- year ;
- document_type ;
- source_pdf ;
- page_number ;
- content_type.

Pourquoi c’est important :

les métadonnées seront utilisées plus tard pour :

- retrieval filtré ;
- citations ;
- monitoring ;
- évaluation ;
- traçabilité.

---

## ProcessingQualityAgent

Fichier :

app/processing/processing_quality_agent.py

Rôle :

- mesurer la qualité du nettoyage ;
- détecter erreurs ou données manquantes ;
- produire une décision PASS / WARNING / FAIL.

---

## ProcessingSupervisorAgent

Fichier :

app/processing/processing_supervisor.py

Rôle :

orchestrer toute la phase :

- nettoyage texte ;
- nettoyage tables ;
- validation metadata ;
- génération rapport qualité.

---

# Formats de sortie

## Pages nettoyées

Format :

.clean_pages.jsonl

Exemple :

json { "company": "ORANGE CI", "year": "2025", "page_number": 42, "cleaned_text": "Le Groupe poursuit sa stratégie de croissance..." }

---

## Tables nettoyées

Format :

.clean_tables.jsonl

Exemple :

json { "company": "ORANGE CI", "page_number": 12, "cleaned_rows": [ ["Indicateurs", "2025", "2024"], ["Chiffre d'affaires", "579.3", "527.2"] ] }

---

# Contrôles qualité réalisés

## Pages

Vérifications :

- pages nettoyées ;
- nombre de mots ;
- erreurs traitement ;
- cohérence metadata.

## Tables

Vérifications :

- lignes vides ;
- colonnes cohérentes ;
- cellules nettoyées ;
- structure exploitable.

## Métadonnées

Vérifications :

- champs obligatoires présents ;
- cohérence des valeurs ;
- complétude globale.

---

# Rapport qualité

Sortie :

data/processed/quality/processing_run_YYYYMMDD_HHMMSS.json

Le rapport contient :

- état global ;
- qualité pages ;
- qualité tables ;
- complétude metadata ;
- erreurs ;
- warnings.

---

# Décisions possibles

## PASS

Le dataset est suffisamment propre pour passer au chunking.

## WARNING

Quelques anomalies existent :

- metadata manquantes ;
- tables partiellement cassées ;
- petits problèmes nettoyage.

Une vérification manuelle peut être nécessaire.

## FAIL

La qualité est insuffisante :

- aucun fichier traité ;
- nombreuses erreurs ;
- metadata absentes ;
- sorties inutilisables.

On ne doit pas continuer vers le chunking.

---

# Commande

Exemple :

python -m app.processing.run_processing --companies "ORANGE CI" --years "2025"

Forcer reconstruction :

python -m app.processing.run_processing --companies "ORANGE CI" --years "2025" --force

---

# Exemple de sortie console

text  Processing terminé! ============================================================ État général : PASS Fichiers texte : 5 Pages nettoyées : 126 Fichiers tables : 5 Tables nettoyées : 28 Complétude metadata : 100.0% Rapport qualité : data/processed/quality/processing_run_20260510_154212.json ============================================================ Décision : processing suffisant pour passer à la 