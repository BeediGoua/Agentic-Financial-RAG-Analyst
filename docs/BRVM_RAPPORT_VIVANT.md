# Rapport vivant BRVM

## Problématique

Les documents financiers BRVM sont hétérogènes. L'assistant doit retrouver des informations exactes avec la société, l'exercice, la page et la provenance.

## Capacités visées

Ingestion, extraction, chunking, embeddings, retrieval hybride, citations fiables, évaluations quantitatives, interface et orchestration agentique.

## Réalisations confirmées

- **G0** : environnement reproductible et CI.
- **G1** : fiabilité de l'ingestion/extraction, validation TLS/URL/PDF, manifestes et chemins sécurisés.
- **G2** : chemins FAISS uniques par fichier source, alignement vecteur/métadonnées, validation des index au chargement, traçabilité des caches, écritures atomiques, filtres symétriques dense/BM25/hybride et révisions Hugging Face cohérentes.
- Revue G2 finale: les sept caches de chunking sont liés à la source, aux filtres, aux paramètres et au contenu JSONL; les couples FAISS/métadonnées sont liés au manifeste, aux SHA-256 et à la révision du modèle; les noms de société sont comparés après canonicalisation exacte.
- Validation finale locale : **148 tests passent** avec 3 avertissements de dépréciation, `pip check` est propre, `compileall` réussit et `git diff --check` réussit.
- Les tests synthétiques couvrent maintenant le chevauchement du splitter, les caches des sept stratégies, le mélange de générations FAISS et les alias exacts `ORAC`, `CIEC`, `SNTS`.

## Limites

Aucune performance Recall@K, MRR ou nDCG n'est revendiquée.
Aucune inférence Ollama ou Hugging Face réelle n'a été déclarée testée sans exécution effective.
Les anciens index FAISS sans manifeste G2 ne sont pas migrés automatiquement et doivent être reconstruits.

## G3 — Benchmark scientifique

- Infrastructure G3 ajoutée pour valider les métriques, annotations, correspondance preuves/chunks, filtres, reranking et reporting.
- Mode fixtures disponible sans réseau ni téléchargement de modèle.
- Le corpus réel BRVM et les jugements vérifiés ne sont pas disponibles dans le dépôt local actuel.
- **Aucune performance BRVM réelle mesurée à ce stade.**
- PR #7 est fusionnée dans `main`; les corrections post-revue sont sur la branche `fix/g3-real-benchmark-completion`.
- Suite complète après corrections: **177 tests passent**.
- `make setup` reste bloqué par une exigence CUDA non disponible dans le registre.
- `make doctor` et `make test` restent bloqués avant pytest par 4 contrôles locaux incomplets.

## État G3

**Infrastructure G3 exécutable** : le runner peut désormais associer les chunks aux preuves indépendamment des identifiants, traiter les recherches vides, calculer les couvertures, appliquer la configuration YAML, séparer les statuts techniques et exporter les résultats par `run_id`.

**Benchmark BRVM réel** : non réalisé. Le dépôt ne contient actuellement ni PDF BRVM réel, ni qrels vérifiés, ni index FAISS réel. Le mode réel retourne donc `REAL_BENCHMARK_NOT_READY`.

Les corrections post-revue portent sur les rangs originaux, la déduplication des alternatives par groupe, la propagation du SHA-256 documentaire et le refus des preuves sans provenance vérifiable. Elles ne constituent aucune mesure réelle BRVM.

Validation locale actuelle: 183 tests pytest réussissent et le smoke test fixtures fonctionne hors ligne. La référence de CI Ubuntu 24.04 reste à obtenir sur GitHub Actions.

## Discours oral

« Après avoir sécurisé l'ingestion des rapports financiers, je me suis concentré sur une autre source de risque : l'intégrité de la chaîne d'indexation. Même avec un moteur FAISS fonctionnel, une réponse peut mélanger les vecteurs, les métadonnées et les documents si les chemins, les caches ou les filtres ne sont pas vérifiés. J'ai donc renforcé l'alignement des vecteurs, la traçabilité des artefacts et l'homogénéité du filtrage dense/BM25/hybride. L'objectif n'était pas d'optimiser les scores de pertinence, mais d'obtenir une base techniquement fiable et vérifiable. »
