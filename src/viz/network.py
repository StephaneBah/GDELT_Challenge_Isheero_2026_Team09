"""Visualisation de graphes — layout force-directed Plotly."""
from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go


def force_layout_graph(
    g: nx.Graph,
    *,
    partition: dict | None = None,
    title: str = "",
    seed: int = 42,
    weight_attr: str = "weight",
    iterations: int = 50,
) -> go.Figure:
    """Trace un graphe en layout force-directed Plotly.

    Args:
        g: graphe NetworkX.
        partition: dict optionnel {node: community_id} pour colorier.
        title: titre.
        seed: graine pour le layout (reproductibilité).
        weight_attr: attribut d'arête utilisé comme poids.
        iterations: itérations spring layout.

    Returns:
        Figure Plotly.
    """
    pos = nx.spring_layout(g, seed=seed, weight=weight_attr, iterations=iterations)

    edge_x, edge_y = [], []
    for u, v in g.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=0.5, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    node_x, node_y, node_text, node_color = [], [], [], []
    for node in g.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(str(node))
        node_color.append(partition.get(node, 0) if partition else 0)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        hoverinfo="text",
        marker=dict(
            size=10,
            color=node_color,
            colorscale="Viridis",
            showscale=bool(partition),
            line_width=1,
        ),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=title,
        showlegend=False,
        hovermode="closest",
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
    )
    return fig
