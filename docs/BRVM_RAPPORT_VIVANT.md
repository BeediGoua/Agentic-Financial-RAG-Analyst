# Rapport vivant BRVM

## Problématique

Les documents financiers BRVM sont hétérogènes. L'assistant doit retrouver des informations exactes avec la société, l'exercice, la page et la provenance.

## Capacités visées

Ingestion, extraction, chunking, embeddings, retrieval hybride, citations fiables, évaluations quantitatives, interface et orchestration agentique.

## Réalisations confirmées

- **G0** : environnement reproductible et CI.
- **G1** : fiabilité de l'ingestion/extraction, validation TLS/URL/PDF, manifestes et chemins sécurisés.
- **G2** : chemins FAISS uniques par fichier source, alignement vecteur/métadonnées, validation des index au chargement, traçabilité des caches, écritures atomiques, filtres symétriques dense/BM25/hybride et révisions Hugging Face cohérentes.

## Limites

Aucune performance Recall@K, MRR ou nDCG n'est revendiquée.
Aucune inférence Ollama ou Hugging Face réelle n'a été déclarée testée sans exécution effective.

## Discours oral

« Après avoir sécurisé l'ingestion des rapports financiers, je me suis concentré sur une autre source de risque : l'intégrité de la chaîne d'indexation. Même avec un moteur FAISS fonctionnel, une réponse peut mélanger les vecteurs, les métadonnées et les documents si les chemins, les caches ou les filtres ne sont pas vérifiés. J'ai donc renforcé l'alignement des vecteurs, la traçabilité des artefacts et l'homogénéité du filtrage dense/BM25/hybride. L'objectif n'était pas d'optimiser les scores de pertinence, mais d'obtenir une base techniquement fiable et vérifiable. »
