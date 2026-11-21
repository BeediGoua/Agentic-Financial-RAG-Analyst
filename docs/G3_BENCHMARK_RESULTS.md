# Résultats G3

## Résultats synthétiques

La suite G3 inclut des fixtures synthétiques destinées uniquement à vérifier les schémas, métriques, filtres, reranking, reporting et reproductibilité. Ces résultats n'ont aucune valeur représentative du retrieval financier BRVM.

Le mode CLI `fixtures` peut être exécuté hors ligne sans Ollama, API externe ou téléchargement de modèle.

Validation synthétique locale : **172 tests passent** au total, dont **24 tests G3 ciblés**. Ces tests vérifient les invariants mais ne mesurent aucune performance réelle du retrieval.

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
