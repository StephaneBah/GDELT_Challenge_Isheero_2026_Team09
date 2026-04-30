"""Orchestrateurs de questions de recherche.

Chaque question est un module exposant une instance `QUESTION` qui implémente
le protocole `src.questions.base.Question`. Les questions composent les
primitives de `src/analytics/`, `src/ml/` et `src/viz/` pour produire un
`Result` partageable (figures + tables + métriques + texte d'insight).

Cette couche est délibérément vide en attendant que l'équipe écrive les Q1,
Q2, Q3 (et plus). Voir `docs/04_architecture.md` et `questions.yaml` pour
la convention d'ajout d'une nouvelle question.
"""
