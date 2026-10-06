"""Topology derivation for the coordinated controller.

Extracted from ``coordinated_controller`` (which re-exports ``edge_map_from_net``
for backward compatibility) to keep that module under the file-size limit. Pure,
sumolib-driven, never mutates the net.
"""
from __future__ import annotations

__all__ = ["edge_map_from_net", "edge_of_lane", "split_edge"]


def edge_of_lane(lane_id: str) -> str:
    """Edge id of a lane id (``"A0A1_0"`` -> ``"A0A1"``)."""
    return lane_id.rsplit("_", 1)[0]


def split_edge(edge_id: str, junctions: frozenset[str]) -> tuple[str, str] | None:
    """Split a grid edge id ``src+dst`` into (src, dst) using known junction ids.

    Edge ids are the concatenation of two junction ids (e.g. ``"A0A1"`` =>
    ``("A0", "A1")``). Edges touching dead-ends (``"left0A0"``, ``"A0left0"``)
    have one endpoint that is not a signalised junction; for those we return the
    split only when *both* endpoints are known junctions, else None. We test the
    prefix against the known-junction set so variable-length ids stay correct.
    """
    for jid in junctions:
        if edge_id.startswith(jid):
            rest = edge_id[len(jid):]
            if rest in junctions:
                return jid, rest
    return None


def edge_map_from_net(net, mode: str = "chain"
                      ) -> tuple[dict[str, list[str]], dict[tuple[str, str], str]]:
    """Derive ``(adjacency, edge_map)`` for ANY sumolib net (grid or real OSM).

    This is the reusable lift of the corridor runner's ``derive_topology`` so any
    net -- grid or real -- can hand the controller an explicit ``edge_map`` that
    maps ``(src_junction, dst_junction) -> edge_id`` (the edge ENTERING ``dst``
    that carries traffic released by ``src``) instead of relying on the grid
    ``f"{src}{dst}"`` string convention (which silently no-ops on real nets).

    ``net`` is a ``sumolib.net.Net`` (read via ``sumolib.net.readNet``).

    ``mode == "single"``: strict -- two TLS are neighbours iff a SINGLE edge
    directly connects a node of ``src`` to a node of ``dst``.
    ``mode == "chain"`` (default): two TLS are neighbours iff a directed path of
    only NON-signalised interior nodes connects them with no intervening TLS; the
    in-edge is the LAST edge on that path (the edge entering ``dst``).

    Returns a fresh ``(adjacency, edge_map)`` and never mutates ``net``. The grid
    fallback path needs neither; this is for real nets (or for deriving a grid map
    explicitly to exercise the same code path in tests).
    """
    from collections import deque

    def _node_to_tls() -> dict[str, str]:
        out: dict[str, str] = {}
        for t in net.getTrafficLights():
            for in_lane, _o, _i in t.getConnections():
                out[in_lane.getEdge().getToNode().getID()] = t.getID()
        return out

    def _tls_nodes() -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for t in net.getTrafficLights():
            out[t.getID()] = {in_lane.getEdge().getToNode().getID()
                              for in_lane, _o, _i in t.getConnections()}
        return out

    node_to_tls = _node_to_tls()
    tls_node_set = set(node_to_tls)
    tls_nodes = _tls_nodes()
    edges = [e for e in net.getEdges() if not e.getID().startswith(":")]
    out_edges_of: dict[str, list] = {}
    for e in edges:
        out_edges_of.setdefault(e.getFromNode().getID(), []).append(e)

    adjacency: dict[str, set[str]] = {t: set() for t in tls_nodes}
    edge_map: dict[tuple[str, str], str] = {}

    if mode == "single":
        for e in edges:
            f = node_to_tls.get(e.getFromNode().getID())
            t = node_to_tls.get(e.getToNode().getID())
            if f and t and f != t:
                adjacency[f].add(t)
                adjacency[t].add(f)
                edge_map[(f, t)] = e.getID()
        return ({k: sorted(v) for k, v in adjacency.items()}, edge_map)

    if mode != "chain":
        raise ValueError(f"mode must be 'chain' or 'single', got {mode!r}")

    for src_tls, nodes in tls_nodes.items():
        for start in nodes:
            q: deque[tuple] = deque(
                (e, e.getID(), 0) for e in out_edges_of.get(start, ()))
            visited: set[str] = set()
            while q:
                e, entry_edge, depth = q.popleft()
                tnode = e.getToNode().getID()
                dst_tls = node_to_tls.get(tnode)
                if dst_tls and dst_tls != src_tls:
                    adjacency[src_tls].add(dst_tls)
                    adjacency[dst_tls].add(src_tls)
                    edge_map.setdefault((src_tls, dst_tls), e.getID())
                    continue
                if tnode in tls_node_set or tnode in visited or depth > 8:
                    continue
                visited.add(tnode)
                for nxt in out_edges_of.get(tnode, ()):
                    q.append((nxt, entry_edge, depth + 1))

    return ({k: sorted(v) for k, v in adjacency.items()}, edge_map)
