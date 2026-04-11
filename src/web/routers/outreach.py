"""Outreach API router."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.jobs.deduplicator import get_todays_queue
from src.network.graph import NetworkGraph
from src.outreach.pipeline import run_outreach_pipeline
from src.web.routers.utils import raise_internal

router = APIRouter(prefix="/api/outreach", tags=["outreach"])

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUTREACH_ROOT = REPO_ROOT / "output" / "outreach"


class ConfirmRequest(BaseModel):
    confirm_action: bool = False


class RejectRequest(BaseModel):
    confirm_action: bool = False
    reason: str = Field(min_length=3)


def _pending_drafts() -> list[Path]:
    drafts: list[Path] = []
    for kind in ("warm_intros", "cold", "recruiter"):
        root = OUTREACH_ROOT / kind
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            if "/approved/" in path.as_posix() or "/rejected/" in path.as_posix():
                continue
            drafts.append(path)
    return sorted(drafts)


def _draft_id(path: Path) -> str:
    return hashlib.sha1(str(path).encode()).hexdigest()[:16]


def _draft_index() -> dict[str, Path]:
    return {_draft_id(path): path for path in _pending_drafts()}


@router.get("/queue")
def outreach_queue() -> dict:
    try:
        graph = NetworkGraph.import_from_json()
        items = []
        for job in get_todays_queue(limit=50):
            company = job.get("company", "")
            classification = "warm_intro" if graph.find_path_to_company(company) else "cold"
            items.append(
                {
                    "job_id": job.get("id"),
                    "company": company,
                    "role": job.get("title", ""),
                    "job_url": job.get("url", ""),
                    "classification": classification,
                }
            )
        return {"items": items, "count": len(items)}
    except Exception as exc:  # pragma: no cover
        raise_internal("Failed to build outreach queue.", exc)


@router.post("/run")
def outreach_run(payload: ConfirmRequest) -> dict:
    try:
        if not payload.confirm_action:
            return {"ok": False, "message": "Confirmation required to run outreach pipeline."}
        summary = run_outreach_pipeline(get_todays_queue(limit=50))
        return {"ok": True, "summary": summary}
    except Exception as exc:  # pragma: no cover
        raise_internal("Failed to run outreach pipeline.", exc)


@router.get("/drafts")
def outreach_drafts() -> dict:
    try:
        items = []
        for path in _pending_drafts():
            items.append(
                {
                    "draft_id": _draft_id(path),
                    "kind": path.parts[-3],
                    "date": path.parts[-2],
                    "filename": path.name,
                    "path": str(path.relative_to(REPO_ROOT)),
                    "content": path.read_text(encoding="utf-8"),
                }
            )
        return {"items": items, "count": len(items)}
    except Exception as exc:  # pragma: no cover
        raise_internal("Failed to list outreach drafts.", exc)


@router.post("/approve/{draft_id}")
def approve_draft(draft_id: str, payload: ConfirmRequest) -> dict:
    try:
        if not payload.confirm_action:
            return {"ok": False, "message": "Confirmation required to approve draft."}
        idx = _draft_index()
        path = idx.get(draft_id)
        if not path:
            return {"ok": False, "message": "Draft not found."}
        approved_dir = path.parent / "approved"
        approved_dir.mkdir(parents=True, exist_ok=True)
        dest = approved_dir / path.name
        shutil.copy2(path, dest)
        path.unlink(missing_ok=True)
        return {"ok": True, "approved_path": str(dest.relative_to(REPO_ROOT))}
    except Exception as exc:  # pragma: no cover
        raise_internal("Failed to approve draft.", exc)


@router.post("/reject/{draft_id}")
def reject_draft(draft_id: str, payload: RejectRequest) -> dict:
    try:
        if not payload.confirm_action:
            return {"ok": False, "message": "Confirmation required to reject draft."}
        idx = _draft_index()
        path = idx.get(draft_id)
        if not path:
            return {"ok": False, "message": "Draft not found."}
        rejected_dir = path.parent / "rejected"
        rejected_dir.mkdir(parents=True, exist_ok=True)
        dest = rejected_dir / path.name
        content = path.read_text(encoding="utf-8")
        dest.write_text(f"{content}\n\n## Rejection Reason\n{payload.reason}\n", encoding="utf-8")
        path.unlink(missing_ok=True)
        return {"ok": True, "rejected_path": str(dest.relative_to(REPO_ROOT))}
    except Exception as exc:  # pragma: no cover
        raise_internal("Failed to reject draft.", exc)
