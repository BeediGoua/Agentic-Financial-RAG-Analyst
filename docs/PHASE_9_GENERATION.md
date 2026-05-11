# PHASE 9 — Generation contrôlée

## Objectif

La phase 9 construit la génération finale du système RAG.

Pipeline :

```text
question
↓
retrieval
↓
reranking
↓
generation
↓
réponse + citations
```

Cette phase produit enfin une réponse utilisateur.

Mais la génération reste :

- contrôlée ;
- sourcée ;
- limitée au contexte ;
- anti-hallucination.

---

# Pourquoi cette phase est importante

Le retrieval et le reranking récupèrent les meilleurs chunks.

Mais l’utilisateur ne veut pas lire directement les chunks.

Il veut :

- une réponse synthétique ;
- concise ;
- compréhensible ;
- avec citations.

La génération transforme donc :

```text
retrieved evidence
```

en :

```text
final answer
```

---

# Principe important

Le LLM ne doit pas répondre librement.

Il doit :

- utiliser seulement le contexte fourni ;
- refuser si l’information est absente ;
- éviter les hallucinations.

Le système doit rester :

```text
grounded
```

c’est-à-dire :

```text
attaché aux documents sources
```

---

# Pourquoi Ollama

Le projet utilise Ollama pour :

- exécuter des LLM localement ;
- éviter les coûts API ;
- garder un pipeline local ;
- tester facilement plusieurs modèles.

Avantages :

- open-source ;
- simple ;
- compatible Mac / Linux / Windows ;
- fonctionne avec Qwen, Llama, Mistral, Gemma, etc.

---

# Modèles recommandés

## qwen2.5:7b

Recommandation principale.

Bon équilibre :

- qualité ;
- vitesse ;
- mémoire ;
- compréhension.

## llama3.1

Alternative possible.

---

# Structure du code

```text
app/
  generation/
    __init__.py
    schemas.py
    prompts.py
    providers.py
    ollama_generator.py
    citation_builder.py
    quality.py
    supervisor.py
    run_generation.py
```

---

# Rôle des fichiers

| Fichier | Rôle |
|---|---|
| schemas.py | structure des réponses générées |
| prompts.py | prompts système et utilisateur |
| providers.py | configuration des providers |
| ollama_generator.py | génération via Ollama |
| citation_builder.py | création des citations |
| quality.py | validation simple |
| supervisor.py | orchestration |
| run_generation.py | CLI |

---

# Fichier important : prompts.py

Le prompt système est très important.

Il impose :

- usage strict du contexte ;
- refus si absent ;
- pas d’invention ;
- style professionnel.

Exemple :

```text
If the answer is not explicitly supported by the context,
answer exactly:
"Information not found in the provided documents."
```

C’est une première défense contre les hallucinations.

---

# Fichier important : ollama_generator.py

Ce fichier communique avec Ollama.

Il :

1. construit le prompt ;
2. envoie la requête ;
3. récupère la réponse ;
4. retourne le texte généré.

Communication :

```text
HTTP API locale
http://localhost:11434
```

---

# Fichier important : citation_builder.py

Ce fichier construit les citations depuis les chunks utilisés.

Chaque citation contient :

- entreprise ;
- année ;
- document ;
- pages ;
- section.

Cela permet :

- traçabilité ;
- auditabilité ;
- vérification humaine.

---

# Exemple de sortie

```json
{
  "answer": "The company mentioned refinancing risk and short-term debt pressure.",
  "status": "answered",
  "citations": [
    {
      "company": "ORANGE CI",
      "page_start": 42,
      "section": "Liquidity Risk"
    }
  ]
}
```

---

# Gestion des réponses absentes

Si l’information n’existe pas dans les documents :

```text
Information not found in the provided documents.
```

Cela réduit :

- hallucinations ;
- réponses inventées ;
- fausse confiance.

---

# Quality checks

La phase vérifie :

- réponse non vide ;
- présence citations ;
- cohérence minimale.

La vraie évaluation viendra plus tard :

- faithfulness ;
- groundedness ;
- hallucination rate ;
- citation accuracy.

---

# Entrées

La phase lit :

```text
data/reranking/runs/reranking_run_*.json
```

---

# Sorties

La phase produit :

```text
data/generation/runs/generation_run_*.json
```

---

# Installation Ollama

## Installer Ollama

https://ollama.com

## Télécharger un modèle

```bash
ollama pull qwen2.5:7b
```

## Lancer Ollama

```bash
ollama serve
```

---

# Commandes

## Génération simple

```bash
python -m app.generation.run_generation
```

## Modèle différent

```bash
python -m app.generation.run_generation --model "qwen2.5:7b"
```

---

# Ce qu’on ne fait pas encore

À cette phase :

- pas encore d’agentic layer ;
- pas encore de multi-step reasoning ;
- pas encore d’évaluation complète ;
- pas encore d’upload PDF dynamique.

---

# Phase suivante

La prochaine étape sera :

```text
PHASE 10 — Agentic Layer
```

Objectif :

- orchestrer retrieval ;
- reranking ;
- génération ;
- query planning ;
- outils spécialisés.

---

# Résumé

La phase 9 transforme :

```text
retrieved evidence
```

en :

```text
source-grounded financial answer
```

C’est la première version complète du RAG.