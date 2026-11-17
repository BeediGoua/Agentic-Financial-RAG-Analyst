# Journal G1 — fiabilisation de l’ingestion et de l’extraction

## Base et périmètre

- Branche de travail : `fix/g1-ingestion-extraction-integrity-20261117`.
- Base locale : `main`/`origin/main` à `2c302b0f79c740fd8a9b09595b1393ae6bd80fd8`; l’arbre était propre avant création de la branche.
- Le rapport de l’archive cite `edaf61c81fcbeebfb6f452440ec05a712e1f6d5a` comme base G0. Le clone fourni est greffé (`grafted`) et ne contient pas cette révision dans son historique ; les tests G0 présents ont été conservés et passent. Ce décalage d’historique doit être vérifié lors de la publication.
- L’archive, ses consignes, le rapport, les deux suites, le patch candidat, les deux recettes et les diagnostics ont été lus. Les propositions candidates n’ont pas été appliquées aveuglément ; les changements ci-dessous ont été vérifiés contre les fichiers de ce clone.

## État initial reproduit

La suite d’acceptation originale a été exécutée avant correction :

```text
.venv/bin/python -m pytest -q tests/test_g1_contracts.py tests/test_g1_orchestration_and_storage.py
28 failed, 6 passed
```

Cas rouges : PDF au faux en-tête, PDF chiffré et PDF sans page acceptés ;
résultats d’extraction texte/table vides ou cache inconnu classés `HEALTHY` ;
échecs BRVM/Sika/macro non propagés ; cache texte vide accepté et extraction
forcée détruisant l’ancien JSONL ; TLS désactivé ; liste d’années non analysée ;
ingestion vide classée saine ; état table non agrégé ; téléchargement HTML,
cache PDF invalide et transfert interrompu non rejetés ; codes de retour CLI
des rapports/extractions/audit incorrects ; sources EDEN manquantes ignorées ;
sortie table détruite lors d’un retry et cache table invalide réutilisé.

## Corrections et justification

| P0 / fichiers et points d’entrée | Cause et impact | Correction et preuve |
| --- | --- | --- |
| **P0-01 — ingestion sans échec silencieux** : `app/ingest/run_all.py:12`, `run_reports.py:21`, `supervisor.py:24`, `ingestion_health.py:20`, `brvm_source.py:385`, `sika_source.py:142`, `macro_source.py:47` | Les exceptions des sources étaient journalisées puis oubliées ; les erreurs de découverte BRVM et les erreurs par ticker Sika disparaissaient ; données EDEN et lots vides pouvaient être considérés comme traités. | `run_all` collecte les échecs des trois sources et sort avec le code 1 ; BRVM conserve les erreurs de découverte dans le rapport ; Sika collecte les erreurs et échoue à la fin du lot ; macro exige les deux fichiers et des observations non vides ; le rapport vide échoue par défaut, `--allow-empty` étant explicite et ne masquant pas les erreurs. Santé ingestion : zéro résultat et erreurs/PDF invalides sont critiques ; les doublons validés restent distincts des nouvelles ingestions. Tests d’acceptation, test Sika sans réseau, découverte BRVM simulée, macro vide simulée et CLI macro en copie isolée. |
| **P0-02 — échec extraction propagé** : `app/extraction/extraction_quality_agent.py:13,100`, `extraction_supervisor.py:41`, `run_extraction.py:12`, `extraction_audit.py:234`, `app/pipeline/run_data_pipeline.py:175,233` | Une liste vide ou un cache incomplet obtenait `HEALTHY` ; le statut table pouvait être masqué par le texte ; les CLI pouvaient retourner zéro après un échec. | Aucune extraction texte/page et aucune entrée de lot table ne sont saines ; un PDF traité sans tableau reste acceptable ; les caches texte doivent être lisibles et complets ; le superviseur retient la gravité maximale ; extraction et audit renvoient un code non nul à l’échec. Le pipeline s’arrête à la première phase non réussie. Tests ciblés et test paramétré d’arrêt après échec ingestion/extraction. |
| **P0-03 — PDF, stockage, caches et manifestes** : `app/ingest/quality.py:22`, `storage.py:58,110,140`, `app/extraction/pdf_text_agent.py:95`, `table_extraction_agent.py:45`, `app/core/atomic.py:12`, `app/core/manifests.py:9,31` | Le contrôle n’examinait que l’en-tête et quelques octets ; les téléchargements écrivaient directement au chemin final ; les caches non vérifiés et les extractions forcées pouvaient laisser des sorties partielles ; les manifestes ne garantissaient pas que le hash corresponde au fichier. | Validation PyMuPDF (type PDF, déchiffrement, pages, lecture, taille) ; téléchargement streamé borné vers `.part`, validation réelle puis `os.replace` ; caches texte/table parseables et cohérents avant réutilisation ; extractions, rapports et manifestes écrits atomiquement ; hash et PDF revalidés avant manifeste `success`, manifestes incohérents exclus de la déduplication. Les sorties antérieures restent intactes si l’extraction échoue. Tests PDF synthétique de bout en bout, HTML/interruption, cache invalide, retry forcé, métadonnées et hash. |
| **P0-04 — TLS** : `app/ingest/brvm_source.py` (initialisation session), `storage.py` (initialisation session), `sika_source.py:71` | `verify=False` et la suppression globale de `InsecureRequestWarning` permettaient des connexions sans validation de certificat, donc des données financières interceptées ou altérées. | Suppression de ces contournements ; Requests conserve sa validation TLS par défaut. `docs/PHASE1_INGESTION.md` documente `REQUESTS_CA_BUNDLE` pour un CA institutionnel. Contrôle `rg` sans occurrence de désactivation et tests simulés vérifiant la configuration. |
| **Défauts associés** : `app/ingest/utils.py:84`, `app/core/manifests.py`, rapports d’ingestion/extraction et `app/pipeline/run_data_pipeline.py:166` | Le filtre année liste plantait ; les caches Sika récents pouvaient être vides/non manifestés ; des rapports qualité et manifests pouvaient être partiels. | Parsing des listes et intervalles bornés ; cache Sika contrôlé par schéma, manifeste, taille et SHA-256 ; écriture atomique des rapports santé/audit/pipeline et vérification des manifestes avant publication. Aucun changement de schéma Pydantic ni de chemins JSONL. |

## Contrôles effectués

- Suite G1 finale : **43 réussis, 0 échoué**.
- Suite complète `pytest -q tests` : **51 réussis, 0 échoué, 0 ignoré** (43 G1 et 8 tests G0/extraction conservés).
- CLI `python -m app.ingest.run_all --only-macro` : vérifiée par sous-processus dans une copie temporaire isolée, sans toucher aux données du dépôt ; code non nul si les deux fichiers EDEN manquent.
- Cas de bout en bout : PDF synthétique téléchargé par réponse HTTP simulée, validé, manifesté puis extrait avec provenance conservée ; interruption HTTP simulée sans PDF final ni fichier temporaire laissé.
- `python -m pip check` : aucune dépendance brisée dans l’environnement de test ciblé.
- `python -m compileall -q app tests`, `git diff --check` : réussis.
- Recherche de `verify=False`, `session.verify = False` et `disable_warnings(` sous `app/` : aucune occurrence.
- L’index Git est resté vide ; aucun script de livraison n’a été modifié.

## Limites d’environnement et livraison

Le Codespace fourni ici est Alpine Linux/musl, alors que le lock G0 et le
workflow ciblent Ubuntu 24.04/glibc. Le bootstrap Python 3.11 depuis le lock a
échoué sur `cuda-bindings==13.5.0` (aucune distribution pour musl). Pour
reproduire les tests, les dépendances directes nécessaires ont été installées
dans la `.venv` Python 3.11.18 ; ce n’est donc pas une installation complète
certifiée depuis `requirements.lock`.

En conséquence, `make doctor` ne passe pas (15/23 contrôles) : Tesseract,
`opencv-python`, `sentence-transformers`, `faiss-cpu`, `python-dotenv`,
`rank-bm25` et `pytest-cov` sont absents, et `urllib3` installé ne correspond
pas au pin attendu. `make test` s’arrête donc dans le doctor avant les tests,
bien que la suite complète exécutée directement passe. L’installation propre
depuis le lock et le workflow GitHub Actions Ubuntu restent à vérifier.

Conformément à la demande de laisser l’ajout, le commit et le push à
l’utilisateur, aucune modification n’a été ajoutée à l’index, commitée ou
poussée. Il n’y a donc pas encore de PR ni de run GitHub Actions à vérifier.
Le code G1 est candidat à revue, mais **G1 n’est pas validé** tant que le lock,
`make doctor`/`make test` et la CI du dernier commit n’ont pas été validés sur
la plateforme cible.
