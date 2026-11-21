# Journal G3 — Benchmark du retrieval

## Contexte

G3 dérive directement du commit G2 `e590fd23b2651738162028ea72b16bbaeb9bec5c`. La PR #6 était ouverte lors de la préparation, donc les travaux G3 sont réalisés sur une branche dédiée dérivée de G2 et ne modifient pas `main`.

## Corrections préflight

- Le supervisor transmet désormais `companies` et `years` au retriever dense.
- Le reranker CrossEncoder valide la longueur et la finitude des scores avant construction des résultats.
- BM25 et dense distinguent corpus absent et résultat vide.
- Les sorties G3 utilisent des IDs de run uniques et des écritures atomiques.

## Implémentation

Modules ajoutés sous `app/evaluation/` :

- schémas Pydantic;
- snapshot de corpus;
- chargement et validation des annotations;
- correspondance preuve/chunk;
- métriques de ranking;
- adaptateurs;
- runner injectables;
- comparaison bootstrap;
- reporting atomique;
- CLI fixtures/réaliste.

## Validation locale

Résultats observés :

- Suite complète locale : **172 tests passent**, dont 24 nouveaux tests G3, avec 3 avertissements de dépréciation.
- Mode fixtures : réussi, avec run ID `0f32b0e5073f487c9b2ead37e0b16815`.
- `pip check` : aucune dépendance cassée.
- `compileall` : réussi.
- `git diff --check` : réussi.
- `make doctor` : `19/23` contrôles; échecs locaux pour Tesseract, `urllib3`, `opencv-python` et `sentence-transformers`.
- `make setup` : échoue sur `cuda-bindings==13.5.0`, introuvable dans le registre disponible.
- `make test` : bloqué avant pytest par le même doctor strict incomplet.
- Mode réel : retourne explicitement `REAL_BENCHMARK_NOT_READY` avec 0 annotation vérifiée et 0 document dans le manifeste.

Commandes prévues :

```bash
.venv/bin/python -m pytest -q tests
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q app tests
git diff --check
.venv/bin/python -m app.evaluation.run_retrieval_eval --mode fixtures
```

## Etat réel

Le benchmark réel n'est pas prêt : aucun PDF BRVM suivi, aucun chunk, embedding ou index réel n'est disponible et aucune question annotée vérifiée n'existe. Les traces historiques de retrieval/reranking ne sont pas utilisées comme vérité terrain.

## Corrections G3 post-revue

- PR #7 fusionnée; le benchmark partait du commit de référence `2b2fa12d8cee5ccc286905a1ca8d2c70f5a33422`.
- Les preuves sont maintenant résolues depuis le SHA-256, les pages, le texte/citation, l'unité et les métadonnées documentaires, indépendamment du `chunk_id`.
- Les recherches validées mais vides produisent des métriques nulles.
- Les statuts techniques sont séparés des moyennes.
- Evidence Coverage@K et All-Evidence@K sont intégrés au runner.
- Les questions `unanswerable` sont conservées séparément.
- Les snapshots comptent réellement les fichiers de chunks, les chunks, les index FAISS et les vecteurs.
- Le CLI réel retourne `REAL_BENCHMARK_NOT_READY` tant que le corpus, les PDF, les SHA-256 ou les annotations vérifiées ne sont pas disponibles.
- Les sorties utilisent un sous-répertoire par `run_id`.

## Corrections G3 post-revue indépendante

- Les métriques utilisent désormais les positions originales des chunks; les listes compressées d'evidence IDs ne sont plus utilisées pour MRR/nDCG.
- Hit@K et MRR@K sont définis sur le chunk classé; Recall@K/nDCG@K dédupliquent les alternatives par groupe indispensable.
- Evidence Coverage@K et All-Evidence@K restent définis au niveau du groupe de preuves.
- `document_sha256` est propagé dans les schémas chunk, embedding et métadonnées vectorielles, avec compatibilité `source_sha256`.
- Un registre documentaire relie les manifests G1 vérifiés aux PDF, avec normalisation Windows/Linux, détection des ambiguïtés et vérification SHA-256.
- Toute provenance absente ou incohérente produit un statut explicite et empêche la correspondance des preuves.

## Résultat de validation

- Suite locale pytest: **183 tests réussis**, 3 avertissements de dépréciation.
- Smoke test `fixtures`: réussi hors ligne.

## Validation post-corrections

- Suite G3 ciblée : **29 tests passent**.
- Suite complète : **177 tests passent**, 3 avertissements de dépréciation.
- `pip check` : aucune dépendance cassée.
- `compileall -q app tests` : réussi.
- `git diff --check` : réussi.
- Mode fixtures : réussi hors ligne, avec un run ID unique.
- Mode réel sans corpus : `REAL_BENCHMARK_NOT_READY`, statut attendu.
- `make setup` : bloqué par `cuda-bindings==13.5.0`, absent du registre disponible.
- `make doctor` : 19/23; échecs pour Tesseract, urllib3, opencv-python et sentence-transformers.
- `make test` : bloqué par le même contrôle doctor avant pytest; pytest direct passe.
