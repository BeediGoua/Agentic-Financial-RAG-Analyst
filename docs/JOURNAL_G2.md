# Journal G2 — intégrité du chunking, embeddings, FAISS et retrieval

## Contexte

G2 sécurise la chaîne documentaire après l'ingestion G1. L'objectif est d'empêcher qu'un vecteur, ses métadonnées ou son document de provenance soient mélangés, écrasés ou filtrés incorrectement.

## FAISS et embeddings

- **Constat** : `FaissIndexBuilder.build_output_paths()` ignorait le nom du fichier d'embeddings et pouvait écraser plusieurs index.
- **Risque** : résultats provenant d'un document différent ou réutilisation d'un cache obsolète.
- **Correction** : sous-répertoire basé sur le nom stable du fichier d'embeddings, validation stricte des dimensions, valeurs finies, normes, stratégies, modèles, identifiants de chunks et provenance.
- **Alignement** : `vector_id` devient la position effective dans FAISS; avant publication, `ntotal`, les métadonnées et les dimensions sont vérifiés.
- **Écriture** : index binaire temporaire vérifié puis promu, métadonnées écrites atomiquement, sauvegarde temporaire permettant une restauration après échec.

## Caches et traçabilité

- Ajout de `app/core/artifact_cache.py` pour associer source, SHA-256, stage, paramètres et empreinte de sortie.
- Les embeddings publient leur manifeste après sortie atomique.
- Les index publient un manifeste couvrant leur source, leurs paramètres et les empreintes de l'index et des métadonnées.

## Retrieval

- Ajout de `app/retrieval/filters.py` et de filtres communs BM25/dense/hybride.
- Ajout de la canonicalisation des sociétés à partir de `config/universe.yaml`, notamment ORAC/ORANGE CI.
- Dense utilise la révision Hugging Face configurée, normalise les requêtes et recherche progressivement jusqu'à trouver les candidats admissibles.
- Chaque index charge ses métadonnées et échoue explicitement en cas de corruption ou de désalignement.
- L'hybride transmet les filtres aux deux moteurs, copie les résultats avant modification et utilise une identité composite stratégie/document/chunk.

## Chunking

- `write_jsonl()` utilise désormais l'écriture atomique G1.
- Les IDs restent déterministes et basés sur stratégie, provenance, pages, indice et texte.
- La stratégie sémantique charge son modèle uniquement lorsqu'elle est réellement utilisée.

## Qualité

Les contrôleurs de chunking, embeddings, FAISS et retrieval retournent désormais un état `FAIL` lorsqu'une erreur technique existe, plutôt qu'un faux succès ou un simple avertissement.

## Validation

- Suite G2 locale sans réseau : 12 tests passent.
- Suite complète locale : 134 tests passent.
- FAISS réel et NumPy sont utilisés dans les tests d'intégrité.
- Aucun téléchargement ou inférence réelle de modèle Hugging Face n'a été exécuté.

## Limites

La migration automatique des anciens index n'est pas exécutée: les anciens artefacts restent non validés et les nouveaux chemins doivent être reconstruits avec `force=True`.
G2 ne mesure pas Recall@K, MRR ou nDCG.
