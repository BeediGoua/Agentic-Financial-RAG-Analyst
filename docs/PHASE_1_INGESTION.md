# Phase 1 : Ingestion Hybride des Données

L'objectif de cette première phase a évolué pour devenir **le socle d'un véritable Analyste Financier IA**. Au lieu de se contenter de récupérer de simples rapports annuels en texte, notre pipeline d'ingestion ("Agentic RAG Analyst") collecte désormais de manière hybride et automatisée trois dimensions critiques :

1. **La composante narrative et comptable** : Rapports et états financiers au format PDF (Scraping BRVM).
2. **La composante marché (Pricing)** : Historique des cours de bourse et volumes (Sika Finance / Richbourse).
3. **La composante macro-économique** : Taux directeurs et inflation de la zone UEMOA (Données BCEAO / EDEN).

L'intégration de ces trois piliers est garantie par une architecture stricte de génération de certificats d'audit (Manifests).

---

## 1. Architecture du code (Le Système Multi-Sources)

L'ingestion est gérée dans le dossier `app/ingest/` et s'appuie sur le dossier `app/core/` pour les fondations.

### A. Le Cœur de l'Audit (Core & Config)
* **`app/core/manifests.py`** : Génère un fichier `manifest.json` standardisé à chaque fois qu'un fichier est ingéré (PDF, CSV). Il calcule une empreinte numérique (`checksum_sha256`), trace l'URL d'origine et horodate l'action. Cela garantit la **provenance** des données pour éviter les hallucinations du modèle.
* **`config/universe.yaml`** : Définit la liste officielle des tickers d'entreprises (SONATEL, CIE CI...) à tracker.
* **`config/sources.yaml`** : Contient les règles de politesse réseau (ex: *Rate Limiting / RPS* pour ne pas surcharger les serveurs sources).

### B. Les Agents Sources
* **`brvm_source.py`** (+ `storage.py`, `quality.py`, `supervisor.py`) : 
  * Gère l'exploration des pages de la BRVM, télécharge les PDF, s'assure qu'ils ne sont pas corrompus et les renomme de manière lisible (`entreprise_annee_type.pdf`).
* **`sika_source.py`** : 
  * Récupère l'historique complet des cours (Open, High, Low, Close) et des volumes de transaction pour chaque entreprise de l'univers. Sauvegarde le tout en format CSV structuré, prêt pour des analyses Pandas.
* **`macro_source.py`** : 
  * Applique une politique "No-Silent-Fail". Il lit les données d'inflation et de taux (fichiers EDEN) et les formate en séries temporelles. S'il manque un fichier source, il crash bruyamment pour alerter l'utilisateur, empêchant l'Agent de travailler avec de fausses données.

### C. L'Orchestrateur
* **`run_all.py`** : C'est le point d'entrée unique. Il permet de lancer de manière sélective ou totale les 3 pipelines d'ingestion.

---

## 2. Comment exécuter et tester (Commandes Terminal)

Tous les scripts doivent être exécutés depuis la racine du projet (`Agentic-Financial-RAG-Analyst/`) sous forme de module Python (avec `-m`).

### A. Le Grand Chelem (Télécharger TOUT)
Pour lancer l'ingestion complète des PDFs, des cours de bourse et de la macro-économie :
```bash
python -m app.ingest.run_all
```

### B. Tester la composante Marché (Sika) uniquement
Si vous voulez vérifier rapidement le scraping boursier sans télécharger tout l'univers, utilisez le mode `--probe` (limite à 1 seul ticker) :
```bash
python -m app.ingest.run_all --only-sika --probe
```

### C. Tester la composante BRVM (PDFs) finement
Le gestionnaire de PDFs est très souple. Voici différentes manières de le piloter :

**Test "Goutte-à-goutte"** (Recommandé pour tester rapidement l'architecture de dossiers) :
```bash
python -m app.ingest.run_all --only-brvm --max-pages 1 --limit 3
```

**Cibler une entreprise et une année spécifique :**
```bash
python -m app.ingest.run_all --only-brvm --companies "CIE CI" --years "2024"
```

**Cibler une plage d'années pour TOUTES les entreprises :**
```bash
python -m app.ingest.run_all --only-brvm --years "2020-2024"
```

**Cibler une plage d'années pour une entreprise précise :**
```bash
python -m app.ingest.run_all --only-brvm --companies "SONATEL" --years "2020-2024"
```

### D. Tester la composante Macro
Assurez-vous d'abord que vos fichiers bruts (`eden_rates.xls`, `eden_cpi_monthly_uemoa.xls`) sont bien placés dans `data/raw/` (tel qu'attendu par le script), sinon le script plantera par sécurité.
```bash
python -m app.ingest.run_all --only-macro
```

---

## 3. Ce qu'il se passe après l'exécution

Une fois les scripts terminés, votre dossier `data/` sera organisé de manière professionnelle :

1. **`data/raw/reports/`** : L'arborescence des PDFs classés par entreprise, année et type. Les fichiers auront des noms significatifs (ex: `orange_ci_2024_etats-financiers_a1b2.pdf`).
2. **`data/raw/sika_csv/`** : Les fichiers CSV contenant l'historique de chaque ticker (ex: `SONATEL_raw.csv`).
3. **`data/bronze/`** : Les fichiers CSV macro-économiques nettoyés (`macro_rates.csv`, `macro_cpi.csv`).
4. **`data/manifests/`** (et `reports/`) : Les fameux fichiers `*.manifest.json`. Ils contiennent les empreintes SHA-256 qui bloquent les doublons, certifient la source et l'heure du téléchargement.
5. **`data/logs/`** : Les rapports de santé (Health Monitor JSON) qui détaillent le taux de succès (success rate) de chaque exécution de pipeline.
