"""Modèles ML entraînés (HuggingFace, sklearn, sentence-transformers).

Cette couche ne contient que des **wrappers de modèles** qui chargent un
artefact entraîné et exposent une fonction d'inférence. Les opérations
analytiques pures (agrégations, points de bascule, graphes) vivent dans
`src/analytics/`.
"""
