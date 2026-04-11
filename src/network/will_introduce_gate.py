"""Warm-intro gate to prevent accidental cold outreach."""

from __future__ import annotations

from src.network.graph import NetworkGraph


def will_introduce_check(contact_id: str, target_company: str) -> dict:
    """
    Return warm-intro eligibility for a contact/company target.

    If no warm path exists, this gate marks outreach as cold and requires
    explicit human override.
    """
    graph = NetworkGraph.import_from_json()
    candidates = graph.get_warm_intro_candidates(target_company)

    candidate = next((c for c in candidates if c["contact_id"] == contact_id), None)
    if not candidate:
        return {
            "can_introduce": False,
            "confidence": 0.0,
            "reasoning": (
                "No warm path found from user to this contact at target company. "
                "Outreach would be cold and requires explicit human override."
            ),
            "suggested_message_tone": "do_not_send_without_override",
        }

    confidence = min(
        1.0,
        (candidate["path_trust_score"] * 0.7)
        + ((candidate["connection_strength"] / 5.0) * 0.3),
    )
    tone = "warm_direct" if confidence >= 0.75 else ("warm_polite" if confidence >= 0.5 else "soft_ask")
    return {
        "can_introduce": True,
        "confidence": round(confidence, 4),
        "reasoning": (
            f"Warm path exists with {candidate['path_hops']} hop(s), "
            f"path trust {candidate['path_trust_score']}, "
            f"and connection strength {candidate['connection_strength']}."
        ),
        "suggested_message_tone": tone,
    }
