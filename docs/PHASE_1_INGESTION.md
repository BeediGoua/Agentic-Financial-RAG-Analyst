# Phase 1 : Ingestion des Données de la BRVM

L'objectif de cette première phase est de centraliser et d'automatiser la récupération des états financiers et rapports annuels des entreprises listées sur la BRVM. Le système fonctionne au travers d'une architecture modulaire "Agentique" pour assurer non seulement la collecte, mais également la validation et le stockage réfléchi de ces documents.

---

## 1. Architecture du code (L'approche Multi-Agents)

Le bloc d'ingestion a été refondu dans le dossier `app/ingest/` de manière complètement orientée objet. L'idée est que chaque étape du processus est confiée à un "Agent" spécialisé (une classe dédiée), le tout piloté par un Superviseur.

* **`BRVMSourceAgent`** (`brvm_source.py`) 
  * **Rôle** : Scraping du site ooficiel de la BRVM.
  * Il explore les pages, identifie les liens PDF, et devine l'entreprise (`infer_company`), l'année (`extract_year`) et le type de rapport concerné.
* **`QualityAgent`** (`quality.py`) 
  * **Rôle** : Gardien de l'intégrité des documents.
  * Après le téléchargement d'un PDF, il s'assure que le fichier est valide (non nul, pas corrompu) et calcule son empreinte (checksum SHA-256) pour bloquer de futurs doublons.
* **`StorageAgent`** (`storage.py`) 
  * **Rôle** : Gère l'écriture sur le disque.
  * Construit automatiquement les arborescences (`data/raw/reports/[Entreprise]/[Année]/`), télécharge les fichiers et enregistre un manifeste (fichier JSO) contenant toutes les métadonnées.
* **`SupervisorAgent`** (`supervisor.py`) 
  * **Rôle** : Le chef d'orchestre.
  * Reçoit la liste des documents découverts par le `BRVMSourceAgent`, puis pour chaque document, il coordonne le `StorageAgent` (téléchargement) et le `QualityAgent` (validation) en respectant un log robuste des succès et échecs.

Tout le système peut être piloté via le point d'entrée universel : **`run_reports.py`**.

---

## 2. Démarrage Rapide : Préparation de l'environnement (`.env`)

Avant de lancer le moindre script, le projet a besoin de comprendre dans quel environnement il évolue.

1. Déplace-toi à la racine du projet :
   ```bash
   cd Agentic-Financial-RAG-Analyst
   ```
2. Crée ton fichier d'environnement (si ce n'est pas déjà fait) à partir de l'exemple fourni :
   ```bash
   # Sur Windows (PowerShell)
   Copy-Item .env.example .env
   ```
3. Ouvre ton nouveau fichier `.env` (qui se trouve à la racine). Normalement, les constantes de l'ingestion sont déjà prêtes par défaut :
   ```env
   DATA_RAW_DIR=data/raw
   DATA_LOGS_DIR=data/logs
   DEFAULT_MAX_PAGES=5
   DEFAULT_LIMIT=10
   ```
   *(Rien d'autre à modifier pour la Phase 1 si tu ne testes que la collecte PDF locale).*

---

## 3. Comment tester et exécuter l'Ingestion (Phase 1)

Tous les scripts doivent être exécutés depuis la racine du projet (`Agentic-Financial-RAG-Analyst/`) sous forme de module Python pour éviter les erreurs d'imports circulaires ou introuvables. 

### A. Le test "Goute-à-goute" (Recommandé pour tester rapidement) 
Si tu veux juste voir comment l'arborescence se crée sans encombrer ta machine avec 50 PDF : on limite le scan à **1 page** du site de la BRVM et la limite de téléchargement à **3 rapports** maximum.

```bash
python -m app.ingest.run_reports --max-pages 1 --limit 3
```
*Le système va lire 1 seule page, stocker les 3 premiers PDF valides trouvés sous `data/raw/reports/`, avec un fichier `*.manifest.json` à côté de chacun.*

### B. Le ciblage : Télécharger une Entreprise ou une Année spécifique 
Tu peux forcer les Agents à filtrer l'ingestion. Imagine que tu ne veuilles télécharger et ranger que les données de la **SONATEL** uniquement pour l'année **2023** :

```bash
python -m app.ingest.run_reports --companies "SONATEL" --years "2023" --max-pages 3
```
*(Tu peux en chercher plusieurs à la fois en utilisant la virgule : `"SONATEL,CIE CI"`)*

### C. Le mode Avion (Collecte Globale massive) 
Si tu veux récupérer tout ce que le système peut trouver sur la BRVM par défaut.

```bash
# Laisser tourner - Prendra le temps de tout indexer
python -m app.ingest.run_reports
```

---

## 4. Ce qu'il se passe après l'exécution

Une fois les commandes terminées, va consulter ton arborescence locale.

1. **Ton dossier brut :**
   ```
   Agentic-Financial-RAG-Analyst/data/raw/reports/sonatel/2023/
   ├── etats_financiers_sonatel_2023.pdf
   └── etats_financiers_sonatel_2023.pdf.manifest.json
   ```
2. **Ton fichier manifest (`.manifest.json`) :** 
   Ouvre-le, tu y retrouveras l'empreinte de qualité (checksum) unique du PDF, ce qui prouvera que le `QualityAgent` a bien diagnostiqué et lu le fichier, bloquant les téléchargements par dessus à l'avenir.
   
3. **Le fichier Log :**
   Inspecte `data/logs/...` un fichier JSON contiendra l'historique de chaque document traité (Ceux qui sont `"status": "success"` ou `"status": "duplicate"`).
