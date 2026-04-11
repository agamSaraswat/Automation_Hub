"""Lightweight trust graph for warm-intro routing inside Automation Hub."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

NETWORK_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "network.json"


@dataclass
class NetworkNode:
    id: str
    name: str
    company: str
    role: str
    linkedin_url: str
    connection_strength: int  # 1-5
    last_contact_date: str
    mutual_connections: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class NetworkEdge:
    from_id: str
    to_id: str
    relationship_type: str  # colleague/friend/mentor/recruiter/alumni
    introduced_via: str
    trust_score: float  # 0.0-1.0
    trust_reasoning: str  # no naked scoring


class NetworkGraph:
    """In-memory graph with JSON flat-file persistence."""

    def __init__(self, user_id: str = "me") -> None:
        self.user_id = user_id
        self.nodes: dict[str, NetworkNode] = {}
        self.edges: list[NetworkEdge] = []

    def add_node(self, node: NetworkNode) -> None:
        if not 1 <= int(node.connection_strength) <= 5:
            raise ValueError("connection_strength must be between 1 and 5")
        self.nodes[node.id] = node

    def add_edge(self, edge: NetworkEdge) -> None:
        edge.trust_score = float(edge.trust_score)
        if not (0.0 <= edge.trust_score <= 1.0):
            raise ValueError("trust_score must be between 0.0 and 1.0")
        if not edge.trust_reasoning.strip():
            raise ValueError("trust_reasoning is required (no naked scoring)")
        if edge.from_id not in self.nodes or edge.to_id not in self.nodes:
            raise ValueError("Both edge endpoints must exist as nodes")
        self.edges.append(edge)

    def _neighbors(self, node_id: str) -> list[tuple[str, NetworkEdge]]:
        pairs: list[tuple[str, NetworkEdge]] = []
        for edge in self.edges:
            if edge.from_id == node_id:
                pairs.append((edge.to_id, edge))
            elif edge.to_id == node_id:
                pairs.append((edge.from_id, edge))
        return pairs

    def _path_trust(self, node_path: list[str]) -> float:
        if len(node_path) <= 1:
            return 1.0
        edge_scores: list[float] = []
        for i in range(len(node_path) - 1):
            a, b = node_path[i], node_path[i + 1]
            for edge in self.edges:
                if (edge.from_id == a and edge.to_id == b) or (edge.from_id == b and edge.to_id == a):
                    edge_scores.append(edge.trust_score)
                    break
        if not edge_scores:
            return 0.0
        return sum(edge_scores) / len(edge_scores)

    def find_path_to_company(self, company: str) -> list[list[NetworkNode]]:
        """Find all simple user->target paths sorted by average trust score."""
        company_l = company.strip().lower()
        target_ids = {nid for nid, n in self.nodes.items() if n.company.strip().lower() == company_l}
        if not target_ids or self.user_id not in self.nodes:
            return []

        raw_paths: list[list[str]] = []

        def dfs(current: str, visited: set[str], path: list[str]) -> None:
            if current in target_ids and len(path) > 1:
                raw_paths.append(path.copy())
            for nxt, _edge in self._neighbors(current):
                if nxt in visited:
                    continue
                visited.add(nxt)
                path.append(nxt)
                dfs(nxt, visited, path)
                path.pop()
                visited.remove(nxt)

        dfs(self.user_id, {self.user_id}, [self.user_id])
        raw_paths.sort(key=self._path_trust, reverse=True)
        return [[self.nodes[node_id] for node_id in path] for path in raw_paths]

    def get_warm_intro_candidates(self, company: str) -> list[dict[str, Any]]:
        paths = self.find_path_to_company(company)
        candidates: list[dict[str, Any]] = []
        for path in paths:
            target = path[-1]
            hop_count = len(path) - 1
            path_ids = [n.id for n in path]
            trust = self._path_trust(path_ids)

            relationship_context: list[dict[str, str]] = []
            for i in range(len(path_ids) - 1):
                a, b = path_ids[i], path_ids[i + 1]
                for edge in self.edges:
                    if (edge.from_id == a and edge.to_id == b) or (edge.from_id == b and edge.to_id == a):
                        relationship_context.append(
                            {
                                "from": self.nodes[a].name,
                                "to": self.nodes[b].name,
                                "relationship_type": edge.relationship_type,
                                "introduced_via": edge.introduced_via,
                                "trust_score": f"{edge.trust_score:.2f}",
                                "trust_reasoning": edge.trust_reasoning,
                            }
                        )
                        break

            ask = (
                f"Hey {target.name}, hope you're doing well — would you be open to a short intro "
                f"to the hiring team for {target.company} ({target.role})?"
            )

            candidates.append(
                {
                    "contact_id": target.id,
                    "contact_name": target.name,
                    "company": target.company,
                    "role": target.role,
                    "connection_strength": target.connection_strength,
                    "path_hops": hop_count,
                    "path_trust_score": round(trust, 4),
                    "relationship_context": relationship_context,
                    "suggested_ask": ask,
                }
            )

        candidates.sort(
            key=lambda c: (c["path_trust_score"], c["connection_strength"], -c["path_hops"]),
            reverse=True,
        )
        return candidates

    def export_to_json(self) -> None:
        NETWORK_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "user_id": self.user_id,
            "nodes": [asdict(n) for n in self.nodes.values()],
            "edges": [asdict(e) for e in self.edges],
        }
        NETWORK_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def import_from_json(cls) -> NetworkGraph:
        graph = cls()
        if not NETWORK_PATH.exists():
            return graph
        data = json.loads(NETWORK_PATH.read_text(encoding="utf-8"))
        graph.user_id = data.get("user_id", "me")
        for node_data in data.get("nodes", []):
            graph.add_node(NetworkNode(**node_data))
        for edge_data in data.get("edges", []):
            try:
                graph.add_edge(NetworkEdge(**edge_data))
            except Exception as exc:
                logger.warning("Skipping invalid edge during import: %s", exc)
        return graph
