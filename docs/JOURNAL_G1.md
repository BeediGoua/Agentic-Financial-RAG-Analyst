# Journal G1 — fiabilisation de l’ingestion et de l’extraction

## Publication initiale de G1

- La PR **#2** a été fusionnée le **17 novembre 2026**.
- Commit de fusion confirmé : `acb936a0679a976100382849f2c0dbed693916bd`.
- La CI G1 exécutée après fusion a réussi.
- La suite validée à cette étape comptait **51 tests réussis** : 43 tests G1
  et 8 tests G0/extraction conservés.
- Les correctifs décrits dans le complément ci-dessous sont postérieurs à la
  PR #2 ; ils n'étaient pas contenus dans cette publication initiale.

## Base et périmètre

- Branche de travail : `fix/g1-ingestion-extraction-integrity-20261117`.
- Base locale au moment de la préparation initiale : `main` à
  `2c302b0f79c740fd8a9b09595b1393ae6bd80fd8`; l’arbre était propre avant
  création de la branche.
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

## Limites de l'environnement local lors de la préparation initiale

Le Codespace fourni ici est Alpine Linux/musl, alors que le lock G0 et le
workflow ciblent Ubuntu 24.04/glibc. Le bootstrap Python 3.11 depuis le lock a
échoué sur `cuda-bindings==13.5.0` (aucune distribution pour musl). Pour
reproduire les tests, les dépendances directes nécessaires ont été installées
dans la `.venv` Python 3.11.18 ; ce n’est donc pas une installation complète
certifiée depuis `requirements.lock`.

À ce moment-là, `make doctor` ne passait pas (15/23 contrôles) : Tesseract,
`opencv-python`, `sentence-transformers`, `faiss-cpu`, `python-dotenv`,
`rank-bm25` et `pytest-cov` sont absents, et `urllib3` installé ne correspond
pas au pin attendu. `make test` s’arrête donc dans le doctor avant les tests,
bien que la suite complète exécutée directement passe. L’installation propre
depuis le lock et le workflow GitHub Actions Ubuntu restent à vérifier.

Cette section est un constat local daté de la préparation de la PR #2. Il ne
remplace pas les résultats GitHub de la publication initiale, indiqués plus
haut, et n'est pas une affirmation sur l'environnement utilisé pour le
complément de clôture ci-dessous.

## Complément G1 — Déduplication et sécurité des URLs

### Déduplication et manifestes

1. **Problème initial :** le superviseur persistait `status="duplicate"` dans
   le manifeste adjacent au PDF, puis le chargement des checksums ignorait ce
   statut.
2. **Impact potentiel :** les exécutions suivantes pouvaient réingérer le
   même contenu ; la provenance du chemin local pouvait également être perdue.
3. **Fichiers concernés :** `app/ingest/supervisor.py`,
   `app/ingest/storage.py`, `app/ingest/ingestion_health.py` et les nouveaux
   tests de clôture.
4. **Cause technique :** le résultat d'une exécution (`duplicate`) était
   confondu avec l'état persistant d'un document validé (`success`).
5. **Correction exacte :** le résultat d'exécution reste `duplicate`, mais le
   manifeste persistant est `success`. Un manifeste success cohérent est
   conservé sans réécriture ; un manifeste absent ou incohérent est reconstruit
   depuis le PDF et le `ReportDocument` vérifiés, avec journalisation lorsqu'un
   ancien manifeste existe. Les manifestes incluent maintenant la taille
   persistée ; les chemins relatifs et absolus sont comparés après résolution.
6. **Tests ajoutés :** 3 exécutions consécutives ; mêmes octets à deux URLs ;
   récupération d'un ancien statut `duplicate`, de JSON corrompu et de hash
   erroné ; vérification de statut, chemin, taille et checksum ; santé ingestion
   avec réussite, doublon, PDF invalide et erreurs distinctes.
7. **Résultats réels :** le test G1 dédié aux corrections et les deux suites
   G1 conservées passent : **90 tests réussis** (43 G1 initiaux et 47 nouveaux
   tests de clôture). La suite complète compte **98 réussis**, dont les 8 tests
   G0/extraction conservés.
8. **Limites résiduelles :** les checksums sont recalculés pour établir
   l'identité des fichiers locaux ; un manifeste absent ne peut pas prouver
   seul la provenance historique, qui est rétablie à partir de la source
   actuellement découverte.

### Validation des URLs et des redirections

1. **Problème initial :** la recherche de sous-chaîne `brvm.org` acceptait des
   hôtes ressemblants ; les requêtes Requests pouvaient suivre des
   redirections vers une destination arbitraire.
2. **Impact potentiel :** requêtes vers des domaines contrôlés par un tiers,
   des services locaux ou des destinations de métadonnées, ainsi que PDF sans
   provenance officiellement approuvée.
3. **Fichiers concernés :** nouveau `app/ingest/url_security.py`,
   `app/ingest/brvm_source.py`, `app/ingest/storage.py`,
   `app/ingest/sika_source.py`, `docs/PHASE1_INGESTION.md` et les tests de
   clôture.
4. **Cause technique :** contrôle de domaine lexical et redirections
   automatiques, sans validation du schéma, de l'autorité, du port et de
   chaque destination.
5. **Correction exacte :** HTTPS seulement ; correspondance exacte des hôtes
   BRVM `brvm.org` et `www.brvm.org` pour HTML et PDF par défaut ; liens PDF
   externes ignorés avec journal structuré. Les domaines PDF additionnels
   nécessitent une approbation explicite par `BRVM_ALLOWED_PDF_HOSTS`.
   Chaque requête HTTP vérifie chaque redirection avant de la suivre et limite
   la chaîne à cinq sauts. Téléchargement vérifie à nouveau l'URL initiale.
   Richbourse possède une liste indépendante (`richbourse.com`,
   `www.richbourse.com`). La vérification TLS Requests reste activée.
6. **Tests ajoutés :** hôtes officiels et malveillants ; validation de
   configuration ; liens HTML/PDF ; redirection officielle ; hôte ressemblant,
   IP locale, port non approuvé, absence de `Location`, trop de redirections,
   HTTP 404, TLS désactivé ; rejet avant réseau ; hôte PDF externe explicitement
   approuvé ; requêtes Richbourse ; intégration simulée complète et variante
   de redirection interdite.
7. **Résultats réels :** la suite de clôture couvre les validations URL,
   redirections, téléchargement et intégration simulée. La suite G1 passe à
   **90/90** et la suite totale à **98/98** ; aucun accès réseau n'est effectué
   par ces tests.
8. **Limites résiduelles :** les listes de domaines ne préviennent pas à elles
   seules le DNS rebinding, un DNS/proxy compromis ou une résolution publique
   vers une IP privée. En production, appliquer aussi une politique d'egress
   réseau : résolveur contrôlé, filtrage des plages loopback/privées/link-local
   et métadonnées, destinations publiques approuvées et proxy d'entreprise
   vérifié. Les hôtes de CDN ne sont pas approuvés automatiquement ; vérifier
   leur propriété et leur usage officiel avant de les inscrire à
   `BRVM_ALLOWED_PDF_HOSTS`. Aucun domaine PDF tiers n'a été ajouté ni déclaré
   officiellement vérifié dans ce complément. La liste effective est une
   configuration d'environnement, pas une preuve d'authenticité documentaire.

### Contrôles de l'environnement de clôture

- `python3.11 --version` : Python 3.11.18.
- `make setup` : **échec** lors de l'installation verrouillée ; aucune
  distribution compatible avec Alpine/musl n'est disponible pour
  `cuda-bindings==13.5.0`.
- `make doctor` : **échec**, 15/23 contrôles ; Tesseract absent, `urllib3`
  installé en 2.8.0 au lieu du pin 2.7.0, et `opencv-python`,
  `sentence-transformers`, `faiss-cpu`, `python-dotenv`, `rank-bm25` et
  `pytest-cov` absents.
- `make test` : **échec avant le lancement de pytest**, car le script s'arrête
  sur le même doctor non vert. Les tests ont été exécutés directement dans
  `.venv`.
- `.venv/bin/python -m pytest -q tests/test_g1_contracts.py
  tests/test_g1_orchestration_and_storage.py tests/test_g1_final_hardening.py` :
  **90 réussis**.
- `.venv/bin/python -m pytest -q tests` : **98 réussis** (0 échec, 0 ignoré).
- `.venv/bin/python -m pip check` : aucune dépendance brisée.
- `.venv/bin/python -m compileall -q app tests` et `git diff --check` :
  réussis.
- Recherche `verify=False`/`disable_warnings` dans `app/` : aucun résultat.
- La CI GitHub Actions de cette branche reste à vérifier après publication ;
  les résultats CI initiaux de la PR #2 sont consignés séparément ci-dessus.
