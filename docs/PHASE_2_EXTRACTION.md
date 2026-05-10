# PHASE 2 — EXTRACTION TEXTE ET TABLES

## Objectif

Cette phase transforme les PDF RAW en données exploitables.

Le pipeline extrait :
- texte page par page ;
- tableaux ;
- métadonnées documentaires ;
- rapports qualité extraction.

Cette phase ne fait PAS encore :
- chunking ;
- embeddings ;
- vector database ;
- retrieval ;
- génération LLM.

---

# Architecture de la phase

RAW PDFs
    ↓
PDFTextExtractionAgent
    ↓
TableExtractionAgent
    ↓
ExtractionQualityAgent
    ↓
Structured extracted data

---

# Structure des dossiers

data/
  extracted/
    pages/
    tables/
    quality/

---

# Agents utilisés

## PDFTextExtractionAgent

Fichier :
app/extraction/pdf_text_agent.py

Rôle :
extraire le texte page par page depuis les PDF.

---

## OCRFallbackAgent

Fichier :
app/extraction/pdf_text_agent.py

Rôle :
détecter les pages mal extraites et utiliser OCR.

Utilise :
- Tesseract OCR ;
- pytesseract ;
- rendu image PyMuPDF.

---

## TableExtractionAgent

Fichier :
app/extraction/table_extraction_agent.py

Rôle :
extraire les tableaux financiers simples avec pdfplumber.

---

## ExtractionQualityAgent

Fichier :
app/extraction/extraction_quality_agent.py

Rôle :
produire des métriques qualité extraction :
- pages vides ;
- taux OCR ;
- erreurs extraction ;
- nombre de tables ;
- état global.

---

## ExtractionSupervisorAgent

Fichier :
app/extraction/extraction_supervisor.py

Rôle :
orchestrer :
- extraction texte ;
- OCR fallback ;
- extraction tables ;
- qualité.

---

# Technologies utilisées

## PyMuPDF

Usage :
- ouverture PDF ;
- extraction texte ;
- rendu image OCR.

---

## pdfplumber

Usage :
- extraction tables ;
- extraction texte structurée.

---

## Tesseract OCR

Usage :
- OCR fallback.

Pourquoi :
- open-source ;
- léger ;
- fonctionne bien FR + EN.

---

# Pourquoi cette phase est critique

Un mauvais texte extrait détruit :
- le chunking ;
- les embeddings ;
- le retrieval ;
- les citations ;
- l’évaluation RAG.












Sans OCR, pour vérifier vite :

python -m app.extraction.run_extraction --companies "ORANGE CI" --years "2025" --disable-ocr
Avec OCR fallback :

python -m app.extraction.run_extraction --companies "ORANGE CI" --years "2025" --force