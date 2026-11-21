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
