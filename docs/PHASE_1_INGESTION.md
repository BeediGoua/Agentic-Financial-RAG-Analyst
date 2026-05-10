# PHASE 1 — INGESTION DES RAPPORTS FINANCIERS

## Objectif

Cette phase construit le pipeline d’ingestion des documents financiers.

Le rôle de cette phase est :
- découvrir les rapports financiers disponibles ;
- télécharger les PDF ;
- vérifier leur validité ;
- éviter les doublons ;
- stocker les fichiers proprement ;
- sauvegarder les métadonnées ;
- produire des logs d’audit.

Cette phase ne fait PAS encore :
- extraction texte ;
- OCR ;
- chunking ;
- embeddings ;
- RAG ;
- LLM.

La sortie finale de cette phase est un stockage RAW fiable des documents.

---

# Architecture de la phase

BRVM / Sources externes
        ↓
Source Agents
        ↓
Supervisor Agent
        ↓
Quality Agent
        ↓
Storage Agent
        ↓
RAW PDF Storage + Metadata + Logs

---

# Structure des dossiers

data/
  raw/
    reports/
  metadata/
  logs/

---

# Agents utilisés

## BRVMSourceAgent

Fichier :
app/ingest/brvm_source.py

Rôle :
- explorer les pages BRVM ;
- détecter les pages documentaires ;
- trouver les liens PDF ;
- extraire :
  - entreprise ;
  - année ;
  - type de document ;
  - URL source.

---

## QualityAgent

Fichier :
app/ingest/agents.py

Rôle :
- vérifier que le fichier est un vrai PDF ;
- calculer le checksum SHA256 ;
- détecter les doublons ;
- contrôler la qualité minimale des fichiers.

---

## LocalStorageAgent

Fichier :
app/ingest/storage.py

Rôle :
- construire l’arborescence des dossiers ;
- télécharger les PDF ;
- sauvegarder les manifests ;
- sauvegarder les logs d’ingestion.

---

## SupervisorAgent

Fichier :
app/ingest/agents.py

Rôle :
orchestrer toute l’ingestion.

Pipeline :
SourceAgent
→ téléchargement
→ validation
→ checksum
→ stockage
→ logs

---

# Métadonnées sauvegardées

```json
{
  "company": "ORANGE CI",
  "ticker": "ORAC",
  "year": 2025,
  "document_type": "annual_report",
  "source_url": "...",
  "checksum_sha256": "...",
  "downloaded_at": "..."
}
```

---

# Pourquoi cette phase est importante

Un mauvais pipeline d’ingestion détruit tout le reste :

mauvais PDF
↓
mauvaise extraction
↓
mauvais chunking
↓
mauvais retrieval
↓
mauvaises réponses RAG
