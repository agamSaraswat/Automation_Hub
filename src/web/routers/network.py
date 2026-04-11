"""Network trust graph API router."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.network.graph import NetworkGraph, NetworkNode
from src.web.routers.utils import raise_internal

router = APIRouter(prefix="/api/network", tags=["network"])


class NodeCreateRequest(BaseModel):
    id: str
    name: str
    company: str
    role: str
    linkedin_url: str = ""
    connection_strength: int = Field(ge=1, le=5)
    last_contact_date: str
    mutual_connections: list[str] = Field(default_factory=list)
    notes: str = ""


@router.get("/nodes")
def list_nodes() -> dict:
    try:
        graph = NetworkGraph.import_from_json()
        return {"items": [asdict(n) for n in graph.nodes.values()], "count": len(graph.nodes)}
    except Exception as exc:  # pragma: no cover
        raise_internal("Failed to list network nodes.", exc)


@router.post("/nodes")
def create_node(payload: NodeCreateRequest) -> dict:
    try:
        graph = NetworkGraph.import_from_json()
        graph.add_node(NetworkNode(**payload.model_dump()))
        graph.export_to_json()
        return {"ok": True, "node_id": payload.id}
    except Exception as exc:  # pragma: no cover
        raise_internal("Failed to create network node.", exc)


@router.get("/path/{company}")
def path_to_company(company: str) -> dict:
    try:
        graph = NetworkGraph.import_from_json()
        paths = graph.find_path_to_company(company)
        serialized = [[asdict(node) for node in path] for path in paths]
        return {"company": company, "paths": serialized, "count": len(serialized)}
    except Exception as exc:  # pragma: no cover
        raise_internal("Failed to find warm paths.", exc)


@router.get("/stats")
def network_stats() -> dict:
    try:
        graph = NetworkGraph.import_from_json()
        companies = {n.company for n in graph.nodes.values() if n.company}
        reachable = [c for c in companies if graph.find_path_to_company(c)]
        avg_trust = (
            sum(edge.trust_score for edge in graph.edges) / len(graph.edges) if graph.edges else 0.0
        )
        return {
            "connection_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "avg_trust_score": round(avg_trust, 4),
            "companies_reachable_via_warm_intro": sorted(reachable),
        }
    except Exception as exc:  # pragma: no cover
        raise_internal("Failed to compute network stats.", exc)
