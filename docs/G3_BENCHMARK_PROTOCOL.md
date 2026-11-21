# G3 — Protocole d'évaluation scientifique du retrieval

## Objectif

G3 mesure la capacité du système à retrouver des preuves financières vérifiables pour une société, un exercice et un document donnés. Il ne mesure pas encore la qualité des réponses générées.

## Corpus figé

Chaque exécution réelle doit produire un snapshot contenant :

- SHA-256 de chaque PDF original;
- nombre et empreintes des manifestes de chunks;
- nombre et empreintes des manifestes FAISS;
- modèles d'embeddings, révisions et stratégies;
- date de création;
- identifiant `snapshot_id` calculé à partir de ces empreintes.

Un changement du corpus ou de la configuration produit une identité différente. Aucun résultat réel ne peut être agrégé à un autre snapshot.

## Références documentaires

La preuve est indépendante du `chunk_id`. Elle contient au minimum :

- SHA-256 du PDF;
- société canonique;
- exercice;
- type documentaire;
- pages de début et de fin;
- citation vérifiée;
- grade de pertinence;
- groupe de preuve.

Les identifiants de groupe représentent des informations indispensables distinctes. Une alternative suffit à couvrir un groupe.

## Échelle de pertinence

- `0` : non pertinent;
- `1` : contexte insuffisant;
- `2` : preuve pertinente;
- `3` : preuve directe et complète.

Les métriques binaires utilisent par défaut `relevant_threshold = 2`. Les IDs non jugés sont traités comme non pertinents seulement pour un calcul provisoire et doivent rester signalés par `judged_fraction` et `unjudged_count`.

## Questions

Les questions sont enregistrées en JSONL dans `data/evaluation/gold/questions.jsonl`. Une question vérifiée doit contenir des preuves réelles, jamais des placeholders. Les questions `unanswerable` doivent documenter une justification distincte : source absente, preuve absente du corpus examiné, hors périmètre ou société/exercice incorrect.

Les splits sont `dev` et `test`. Le split `dev` sert uniquement aux réglages. Le split `test` est réservé à la mesure finale. Les questions liées au même document ou au même fait doivent autant que possible rester dans le même split.

## Pooling et jugement

Les candidats sont produits par BM25, Dense MiniLM, Dense E5 et les configurations hybrides à une profondeur déclarée. Les candidats manuels sont ajoutés aux PDFs. Ils sont dédupliqués par identité de preuve puis jugés indépendamment de la méthode à l'origine du candidat. Les éléments non jugés ne sont pas transformés silencieusement en pertinence positive ou négative définitive.

Une deuxième revue humaine sur un sous-échantillon doit être enregistrée séparément. Une proposition de modèle ne constitue pas une annotation vérifiée automatiquement.

## Correspondance preuve/chunk

Une correspondance documentaire exige :

1. le même SHA-256 documentaire;
2. une plage de pages compatible;
3. une citation normalisée présente dans le chunk;
4. une relation ligne/colonne vérifiée pour les tableaux.

Les métriques sont distinguées :

- hit documentaire;
- hit de page;
- hit de preuve;
- `Evidence Coverage@K`;
- `All-Evidence@K`.

## Métriques

- Hit@K;
- Recall@K;
- Precision@K;
- MRR@K;
- nDCG@K avec gain `2**grade - 1` et réduction `log2(rank + 2)`;
- couverture des groupes de preuves.

Le Recall est un recall relatif aux preuves connues si le pooling est incomplet. Les résultats du top-K non jugés sont marqués provisoires.

## Comparaison

Les comparaisons doivent utiliser le même snapshot, les mêmes questions, filtres, seuil de pertinence et profondeur K. Les poids hybrides ne sont choisis que sur `dev`. Les pools identiques sont obligatoires pour les expériences avec/sans reranking.

Pour un nombre limité de questions, une répétition appariée bootstrap à 1000 échantillons est décrite comme exploratoire. Les questions dépendantes du même document doivent idéalement utiliser un bootstrap groupé.

## Statuts techniques

- `success` : recherche terminée avec candidats;
- `empty` : recherche terminée sans candidat admissible;
- `missing_corpus` : corpus/index attendu absent;
- `invalid_index` : index ou manifeste invalide;
- `model_unavailable` : modèle requis absent;
- `error` : autre erreur technique.

Une erreur technique n'est jamais comptée comme rappel nul.

## Latence

Le rapport doit séparer cold start et warm query, conserver médiane, moyenne et p95, et enregistrer CPU/GPU, nombre de threads, batch size et modèle. BM25 doit mesurer séparément l'accès/reconstruction de l'index et le scoring.

## Limites actuelles

À ce stade, aucun PDF BRVM ni aucun index réel n'est disponible dans le dépôt de travail. Aucun jeu de questions vérifié n'est donc publié et aucune performance BRVM réelle n'est revendiquée.
