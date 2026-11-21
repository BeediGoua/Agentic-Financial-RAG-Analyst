# Résultats G3

## Résultats synthétiques

La suite G3 inclut des fixtures synthétiques destinées uniquement à vérifier les schémas, métriques, filtres, reranking, reporting et reproductibilité. Ces résultats n'ont aucune valeur représentative du retrieval financier BRVM.

Le mode CLI `fixtures` peut être exécuté hors ligne sans Ollama, API externe ou téléchargement de modèle.

Avant les corrections post-revue, la référence audité comptait **172 tests réussis**. Après les corrections G3 post-revue, la suite complète compte **177 tests réussis**, dont **29 tests G3 ciblés**. Ces tests vérifient les invariants mais ne mesurent aucune performance réelle du retrieval.

## Résultats BRVM réels

**Aucune performance BRVM réelle mesurée à ce stade.**

Corpus actuellement disponible localement :

- documents PDF suivis : `0`;
- documents vérifiés disponibles : `0`;
- chunks réels : `0`;
- embeddings réels : `0`;
- index FAISS réels : `0`;
- questions vérifiées : `0`;
- jugements vérifiés : `0`.

Les deux fichiers présents sous `data/retrieval/runs` et `data/reranking/runs` sont des traces historiques et ne constituent pas des qrels.

## Corrections vérifiées

- Correspondance indépendante des IDs de preuve et de chunk;
- correspondance avec SHA-256, pages, citation, nombre et unité;
- rejet des preuves provenant d'un autre document;
- résultats nulls pour une recherche valide sans résultat;
- séparation des erreurs techniques;
- Evidence Coverage@K et All-Evidence@K;
- statistiques réelles du snapshot;
- mode réel avec statut explicite `REAL_BENCHMARK_NOT_READY`;
- sorties JSON, CSV, Markdown dans un répertoire unique par `run_id`.

## Unités métriques verrouillées

- `Hit@K` : fraction des recherches dont un chunk classé couvre au moins un groupe pertinent.
- `MRR@K` : rang du premier chunk classé pertinent, sur la liste complète.
- `nDCG@K` : gains des groupes d'evidence nouvellement couverts à chaque rang de chunk.
- `Recall@K` : groupes indispensables uniques couverts divisés par tous les groupes indispensables.
- `Evidence Coverage@K` : groupes de preuves uniques couverts par les résultats jusqu'à K.
- `All-Evidence@K` : booléen indiquant que tous les groupes ont été couverts.

Les alternatives d'un même groupe ne comptent pas plusieurs fois. Les chunks redondants ne créent aucun gain supplémentaire.

Validation locale: **183 tests pytest réussissent**; le smoke test hors ligne fixtures réussit. `make setup`, `make doctor` et `make test` restent soumis aux limitations d'environnement déjà identifiées.

## Distinction d'état

**Infrastructure G3 exécutable** : le code peut construire BM25, dense et hybride, appliquer les filtres, résoudre les preuves et produire les rapports lorsqu'un snapshot vérifié est fourni.

**Benchmark BRVM réel** : aucune mesure n'est disponible tant qu'aucun PDF, SHA-256 vérifié et jugement vérifié réel n'est fourni.
