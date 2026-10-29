# AI & Machine Learning Engineer 🚀

## Présentation

Ce dépôt regroupe l'ensemble de mes travaux pratiques, expérimentations et projets réalisés dans le cadre d'un programme intensif de 12 semaines en **AI & Machine Learning Engineering**.

L'objectif est de développer des compétences techniques solides dans la conception de pipelines de données, le développement et l'évaluation de modèles de Machine Learning, le Deep Learning, les applications basées sur les Large Language Models (LLM), ainsi que le déploiement et la maintenance de solutions d'intelligence artificielle.

L'approche est orientée projets, avec une attention particulière portée à la qualité du code, à la reproductibilité des expériences, aux tests, à la documentation et à l'évaluation des performances.

## 🎯 Objectifs

- Construire des pipelines de données fiables, testés et reproductibles.
- Développer, comparer et optimiser des modèles de Machine Learning.
- Entraîner et évaluer des réseaux de neurones avec PyTorch.
- Exploiter les Transformers et les modèles préentraînés pour des tâches de Deep Learning et de NLP.
- Développer des applications basées sur les LLM, les embeddings, le RAG et les agents IA.
- Évaluer les performances, analyser les erreurs et identifier les limites des systèmes d'IA.
- Exposer des modèles via des API et les déployer avec des outils de conteneurisation et de MLOps.
- Concevoir des projets complets, documentés, testés et présentables en environnement professionnel.

## 🗺️ Programme de formation

### Phase 1 — Data Engineering for ML
**Semaines 1–2**

- Préparation, nettoyage et analyse exploratoire des données.
- Manipulation des données avec Pandas et NumPy.
- Requêtes SQL avancées et optimisation.
- Feature engineering et contrôle de la qualité des données.
- Pipelines de transformation avec scikit-learn.
- Tests de données et prévention du data leakage.

**Livrable :** un pipeline de données testé, documenté et reproductible.

### Phase 2 — Machine Learning avancé
**Semaines 3–4**

- Régression linéaire et logistique.
- Arbres de décision, Random Forest, SVM et Gradient Boosting.
- Validation croisée et stratégies de validation adaptées aux données.
- Gestion du déséquilibre des classes et prévention du surapprentissage.
- Optimisation des hyperparamètres avec Optuna.
- Évaluation avec des métriques adaptées aux objectifs.
- Interprétabilité des modèles avec SHAP.
- Introduction au clustering et à la détection d'anomalies.

**Livrable :** un benchmark expérimental comparant au moins quatre approches, avec analyse des erreurs et justification des résultats.

### Phase 3 — Deep Learning & Transformers
**Semaines 5–6**

- Tenseurs, autograd et graphes de calcul avec PyTorch.
- Construction et entraînement de réseaux de neurones.
- Fonctions de perte, optimisateurs et rétropropagation.
- Régularisation, normalisation et optimisation du taux d'apprentissage.
- Réseaux convolutifs (CNN) et transfert d'apprentissage.
- NLP, tokenisation et embeddings.
- Attention, self-attention et architecture Transformer.
- Utilisation de modèles préentraînés avec Hugging Face.
- Introduction au fine-tuning et aux méthodes LoRA/PEFT.

**Livrable :** un modèle de classification de texte ou d'images, accompagné d'une comparaison expérimentale et d'un rapport d'erreurs.

### Phase 4 — LLM, RAG & agents IA
**Semaines 7–9**

- Fonctionnement général des Large Language Models.
- Prompt engineering et génération de sorties structurées.
- Intégration de modèles via API et utilisation de modèles ouverts.
- Embeddings et recherche sémantique.
- Découpage de documents, indexation et bases vectorielles.
- Retrieval-Augmented Generation (RAG).
- Recherche hybride, reranking et traçabilité des sources.
- Évaluation de la pertinence et de la fidélité des réponses.
- Développement d'agents IA utilisant des outils.
- Sécurité des applications LLM et protection contre les injections de prompt.

**Livrable :** un assistant RAG construit sur un corpus réel, évalué sur au moins 50 questions de test, avec des métriques et une analyse des échecs.

### Phase 5 — MLOps, API & déploiement
**Semaines 10–11**

- Développement d'API avec FastAPI et Pydantic.
- Chargement et sérialisation des modèles.
- Conteneurisation avec Docker et Docker Compose.
- Tests unitaires et tests d'intégration avec pytest.
- Gestion des secrets et des variables d'environnement.
- Suivi des expérimentations avec MLflow.
- Versionnement des données et des modèles avec une introduction à DVC.
- Automatisation des tests avec GitHub Actions.
- Déploiement de services d'intelligence artificielle.
- Monitoring des logs, de la latence, des erreurs et des performances.

**Livrable :** un service IA conteneurisé et déployé, avec API documentée, tests automatisés et procédure de reproduction.

### Phase 6 — Projet intégrateur
**Semaine 12**

- Identification d'un problème concret et des besoins des utilisateurs.
- Collecte et préparation des données.
- Choix et justification de l'approche IA.
- Expérimentation et comparaison des solutions.
- Évaluation des performances et analyse des limites.
- Intégration du modèle dans une API et, si nécessaire, une interface utilisateur.
- Tests, conteneurisation et documentation.
- Démonstration et soutenance technique.

**Livrable final :** un projet complet publié sur GitHub, documenté, reproductible et testé, avec des résultats mesurables et un déploiement lorsque les ressources le permettent.

## 🛠️ Stack technique

| Domaine | Technologies |
|---|---|
| Programmation et données | Python, SQL, NumPy, Pandas |
| Data Engineering | scikit-learn Pipelines, tests de données |
| Machine Learning | scikit-learn, XGBoost ou CatBoost |
| Optimisation et interprétabilité | Optuna, SHAP |
| Deep Learning | PyTorch |
| NLP et Transformers | Hugging Face |
| IA générative | LLM, APIs, embeddings, prompt engineering |
| RAG et agents IA | FAISS ou Chroma, recherche sémantique, agents avec outils |
| Développement d'API | FastAPI, Pydantic |
| Tests et conteneurisation | pytest, Docker, Docker Compose |
| MLOps et automatisation | MLflow, DVC, GitHub Actions |
| Gestion du code | Git, GitHub |

## 📂 Organisation du dépôt

Le dépôt est organisé par phase de formation afin de faciliter le suivi de la progression, la consultation des exercices et la reproduction des projets.

```text
ai-machine-learning-engineer/
├── 01-data-engineering-for-ml/
├── 02-advanced-machine-learning/
├── 03-deep-learning-transformers/
├── 04-llm-rag-ai-agents/
├── 05-mlops-deployment/
├── 06-capstone-project/
├── datasets/
├── docs/
├── requirements.txt
└── README.md
```

Cette structure constitue une proposition d'organisation : elle pourra être adaptée à la structure réelle du dépôt.

## 📊 Méthodologie

Le programme privilégie une approche pratique fondée sur trois composantes :

- **20 % de théorie :** compréhension des principes, des mathématiques et des choix techniques.
- **60 % de pratique :** implémentation, expérimentation, comparaison et correction.
- **20 % de restitution :** tests, documentation, revue de code et présentation des résultats.

Chaque livrable doit permettre de comprendre les choix techniques, de reproduire les expériences et d'évaluer objectivement les résultats.

## 🎓 Résultats attendus

À l'issue du programme, les travaux doivent couvrir six réalisations principales :

1. Un pipeline de données reproductible.
2. Un benchmark rigoureux de modèles de Machine Learning.
3. Un projet de Deep Learning avec comparaison expérimentale.
4. Un assistant RAG évalué quantitativement.
5. Un service IA testé, conteneurisé et déployé.
6. Un projet intégrateur démontrant la capacité à concevoir une solution IA de bout en bout.

## 📌 Philosophie du projet

L'objectif n'est pas de maîtriser superficiellement un grand nombre d'outils, mais de développer la capacité à concevoir, expérimenter, évaluer et livrer des solutions d'intelligence artificielle fiables.

La priorité est donnée à la compréhension technique, à la qualité des données, à la rigueur expérimentale, à la reproductibilité et à la mise en production.

---

**AI & Machine Learning Engineering | Data Engineering · Machine Learning · Deep Learning · LLM · RAG · MLOps**
