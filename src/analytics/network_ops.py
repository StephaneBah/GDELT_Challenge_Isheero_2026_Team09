"""Opérations sur graphes — construction et détection de communautés.

Primitives pures réutilisables pour toute analyse de réseau (acteurs, médias,
domaines). Aucune dépendance modèle entraîné. Utilisable depuis toute question
(en pratique, surtout Q3 — le réseau).
"""
from __future__ import annotations

import logging
from typing import Iterable

import networkx as nx
import pandas as pd

logger = logging.getLogger(__name__)


def build_graph_from_edges(
    edges: pd.DataFrame,
    *,
    src_col: str = "src",
    dst_col: str = "dst",
    weight_col: str = "weight",
    directed: bool = False,
) -> nx.Graph:
    """Construit un graphe pondéré à partir d'un DataFrame d'arêtes."""
    g = nx.DiGraph() if directed else nx.Graph()
    for _, row in edges.iterrows():
        a, b = row[src_col], row[dst_col]
        if a == b:
            continue
        w = float(row[weight_col])
        if g.has_edge(a, b):
            g[a][b]["weight"] += w
        else:
            g.add_edge(a, b, weight=w)
    logger.info(
        "Graphe : %d nœuds, %d arêtes",
        g.number_of_nodes(),
        g.number_of_edges(),
    )
    return g


def build_actor_graph(
    df: pd.DataFrame,
    *,
    actor_a_col: str = "Actor1Code",
    actor_b_col: str = "Actor2Code",
    type_a_col: str = "Actor1Type1Code",
    type_b_col: str = "Actor2Type1Code",
    weight_col: str = "NumMentions",
    actor_type_filter: tuple[str, ...] = ("GOV", "MIL", "IGO", "NGO"),
) -> nx.Graph:
    """Graphe d'acteurs filtré sur les types politiques (cf. doctrine).

    Filtre par défaut sur GOV/MIL/IGO/NGO pour éliminer le bruit (cf. limite #5
    documentée dans docs/01_doctrine.md).
    """
    sub = df.dropna(subset=[actor_a_col, actor_b_col]).copy()
    if actor_type_filter:
        mask = sub[type_a_col].isin(actor_type_filter) | sub[type_b_col].isin(
            actor_type_filter
        )
        sub = sub[mask]

    edges = (
        sub.groupby([actor_a_col, actor_b_col])[weight_col]
        .sum()
        .reset_index()
        .rename(columns={actor_a_col: "src", actor_b_col: "dst", weight_col: "weight"})
    )
    return build_graph_from_edges(edges)


def detect_communities(g: nx.Graph) -> dict:
    """Détecte les communautés Louvain sur graphe pondéré.

    Retourne un dict {node: community_id}. Tente d'abord python-louvain ;
    fallback sur l'implémentation NetworkX si la lib n'est pas installée.
    """
    try:
        from community import community_louvain  # python-louvain

        return community_louvain.best_partition(g, weight="weight", random_state=42)
    except ImportError:
        from networkx.algorithms.community import louvain_communities

        comms = louvain_communities(g, weight="weight", seed=42)
        return {n: i for i, c in enumerate(comms) for n in c}


def degree_variation(
    g_pre: nx.Graph,
    g_post: nx.Graph,
    *,
    nodes: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Compare le degré pondéré d'un nœud entre deux graphes.

    Utilisé pour Q3 (recomposition pré/post juillet 2023).
    """
    if nodes is None:
        nodes = set(g_pre.nodes) | set(g_post.nodes)
    rows = []
    for n in nodes:
        d_pre = sum(d.get("weight", 0) for _, _, d in g_pre.edges(n, data=True)) if n in g_pre else 0
        d_post = sum(d.get("weight", 0) for _, _, d in g_post.edges(n, data=True)) if n in g_post else 0
        rows.append({"node": n, "degree_pre": d_pre, "degree_post": d_post})
    out = pd.DataFrame(rows)
    out["delta"] = out["degree_post"] - out["degree_pre"]
    out["delta_pct"] = out.apply(
        lambda r: (r["delta"] / r["degree_pre"] * 100) if r["degree_pre"] else float("inf"),
        axis=1,
    )
    return out.sort_values("delta", key=abs, ascending=False).reset_index(drop=True)
