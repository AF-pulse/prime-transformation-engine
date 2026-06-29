"""Local Transformation Object instantiation from governed PrimeMind evidence.

This module is intentionally narrow:

* read governed DBA/PTE knowledge through PrimeMind,
* build a local grounding packet,
* instantiate one local JSON Transformation Object,
* validate that missing grounding fails closed.

It does not orchestrate, execute workflows, write to PrimeMind, write to
ProMind, start an API server, persist graph state, or make autonomous decisions.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


OBJECT_ID = "PTE-101"
OBJECT_TITLE = "Instantiate One Governed Transformation Object"
OBJECT_INTENT = (
    "Create the minimum runtime capability required for Prime Transformation "
    "Engine to instantiate governed Transformation Objects."
)
DEFAULT_BASE_URL = (
    "https://primemind-api.calmbush-638da63e.westeurope.azurecontainerapps.io"
)
REQUIRED_DBA_IDENTIFIERS = (
    "DBA-08",
    "DBA-09",
    "DBA-10",
)


@dataclass(frozen=True)
class RuntimeConfig:
    base_url: str
    bootstrap_token: str


class PrimeMindReadOnlyClient:
    def __init__(self, config: RuntimeConfig) -> None:
        self.base_url = config.base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {config.bootstrap_token}"}

    def identity_context(self) -> dict[str, Any]:
        return self._get_json("/api/identity/context")

    def search(self, query: str, top: int = 5) -> dict[str, Any]:
        params = urlencode({"q": query, "top": top})
        return self._get_json(f"/api/reference/knowledge/search?{params}")

    def retrieve(self, identifier: str) -> dict[str, Any]:
        safe_identifier = quote(identifier, safe="")
        return self._get_json(f"/api/reference/knowledge/{safe_identifier}")

    def _get_json(self, path: str) -> dict[str, Any]:
        request = Request(f"{self.base_url}{path}", headers=self._headers, method="GET")
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


def load_runtime_config(env_path: Path | None = None) -> RuntimeConfig:
    values = dict(os.environ)
    if env_path and env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.strip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values.setdefault(key, value)

    token = values.get("PRIMEMIND_ENGINE_BOOTSTRAP_TOKEN")
    if not token:
        raise RuntimeError("PRIMEMIND_ENGINE_BOOTSTRAP_TOKEN is required")

    return RuntimeConfig(
        base_url=values.get("PRIMEMIND_API_BASE_URL", DEFAULT_BASE_URL),
        bootstrap_token=token,
    )


def build_grounding_packet(client: PrimeMindReadOnlyClient) -> dict[str, Any]:
    identity = client.identity_context()
    if identity.get("identity_id") != "prime-transformation-engine":
        raise RuntimeError("Engine identity was not established")

    searches = [
        {
            "query": "Transformation Objects",
            "response": client.search("Transformation Objects", top=5),
        },
        {
            "query": "Cognitive Transformation Layers",
            "response": client.search("Cognitive Transformation Layers", top=5),
        },
    ]
    retrieved = [
        _reference_from_retrieval(identifier, client.retrieve(identifier))
        for identifier in REQUIRED_DBA_IDENTIFIERS
    ]
    search_refs = _references_from_searches(searches)
    references = _dedupe_references([*retrieved, *search_refs])

    packet = {
        "source": "PrimeMind governed DBA/PTE read-only retrieval",
        "identity": {
            "identity_id": identity.get("identity_id"),
            "tenant_id": identity.get("tenant_id"),
            "identity_type": identity.get("identity_type"),
            "groups": identity.get("groups", []),
        },
        "queries": [search["query"] for search in searches],
        "references": references,
        "behavioral_constraints": _behavioral_constraints(),
        "open_assumptions": _open_assumptions(references),
    }
    _require_grounding(packet)
    return packet


def instantiate_transformation_object(grounding: dict[str, Any]) -> dict[str, Any]:
    _require_grounding(grounding)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "id": OBJECT_ID,
        "title": OBJECT_TITLE,
        "intent": OBJECT_INTENT,
        "ctl_layer": "CTL-E",
        "substrate": "ET",
        "state": "grounded",
        "grounding": grounding,
        "provenance": {
            "created_from": "governed PrimeMind DBA/PTE retrieval",
            "created_from_identity": grounding["identity"]["identity_id"],
            "reference_ids": [reference["id"] for reference in grounding["references"]],
            "publication_statuses": sorted(
                {
                    reference["publication_status"]
                    for reference in grounding["references"]
                    if reference.get("publication_status")
                }
            ),
            "effective_crystal_ids": sorted(
                {
                    reference["effective_crystal_id"]
                    for reference in grounding["references"]
                    if reference.get("effective_crystal_id")
                }
            ),
        },
        "created_at": now,
        "created_by": grounding["identity"]["identity_id"],
    }


def validate_transformation_object(obj: dict[str, Any]) -> None:
    required_fields = (
        "id",
        "title",
        "intent",
        "ctl_layer",
        "substrate",
        "state",
        "grounding",
        "provenance",
        "created_at",
        "created_by",
    )
    missing = [field for field in required_fields if not obj.get(field)]
    if missing:
        raise ValueError(f"Transformation Object missing fields: {', '.join(missing)}")
    if obj["created_by"] != "prime-transformation-engine":
        raise ValueError("Transformation Object must be created by Engine identity")
    _require_grounding(obj["grounding"])


def write_transformation_object(obj: dict[str, Any], path: Path) -> None:
    validate_transformation_object(obj)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _reference_from_retrieval(identifier: str, payload: dict[str, Any]) -> dict[str, Any]:
    chunks = payload.get("chunks") if isinstance(payload.get("chunks"), list) else []
    chunk_ids = [chunk.get("chunk_id") or chunk.get("id") for chunk in chunks if isinstance(chunk, dict)]
    return {
        "id": identifier,
        "title": payload.get("title") or identifier,
        "retrieval_path": f"/api/reference/knowledge/{identifier}",
        "relevance": _relevance_for(identifier),
        "publication_status": payload.get("publication_status"),
        "provenance": payload.get("provenance"),
        "chunk_ids": [chunk_id for chunk_id in chunk_ids if chunk_id],
        "effective_crystal_id": payload.get("effective_crystal_id"),
        "citation_status": "direct retrieval exposed provenance/chunk/crystal metadata; explicit citation field not present",
    }


def _references_from_searches(searches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for search in searches:
        results = search["response"].get("results", [])
        if not isinstance(results, list):
            continue
        for result in results[:3]:
            if not isinstance(result, dict):
                continue
            references.append(
                {
                    "id": result.get("id") or result.get("chunk_id"),
                    "title": result.get("title"),
                    "retrieval_path": "/api/reference/knowledge/search",
                    "search_query": search["query"],
                    "relevance": f"Returned by governed search for {search['query']}.",
                    "publication_status": result.get("publication_status"),
                    "provenance": result.get("provenance"),
                    "chunk_ids": [result.get("chunk_id")] if result.get("chunk_id") else [],
                    "knowledge_object_id": result.get("knowledge_object_id"),
                    "effective_crystal_id": result.get("effective_crystal_id"),
                    "citation_status": "search result exposed provenance/chunk/crystal metadata; explicit citation field not present",
                }
            )
    return [reference for reference in references if reference.get("id")]


def _dedupe_references(references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for reference in references:
        key = reference["id"]
        if key in seen:
            continue
        seen.add(key)
        result.append(reference)
    return result


def _behavioral_constraints() -> list[str]:
    return [
        "Instantiate exactly one local Transformation Object.",
        "Use governed PrimeMind DBA/PTE retrieval and search as grounding.",
        "Preserve provenance, publication status, chunk identity, and effective crystal identity when citations are not exposed directly.",
        "Assign CTL-E and ET because this object concerns minimum executable runtime capability.",
        "Persist locally only; do not orchestrate, deploy, write to PrimeMind, write to ProMind, mutate IAM, or persist graph state.",
        "Fail closed when grounding references or provenance are missing.",
    ]


def _open_assumptions(references: list[dict[str, Any]]) -> list[str]:
    assumptions = []
    if not any(reference.get("citation_status") for reference in references):
        assumptions.append("Explicit citation fields were not exposed by the retrieval response.")
    if not any(reference.get("id") == "DBA-09" for reference in references):
        assumptions.append("Transformation Lineage DBA retrieval was not available.")
    return assumptions


def _require_grounding(packet: dict[str, Any]) -> None:
    references = packet.get("references")
    if not isinstance(references, list) or not references:
        raise ValueError("Grounding references are required")
    for reference in references:
        if not reference.get("provenance"):
            raise ValueError(f"Grounding reference {reference.get('id')} lacks provenance")
        if not reference.get("publication_status"):
            raise ValueError(f"Grounding reference {reference.get('id')} lacks publication_status")
        if not reference.get("effective_crystal_id"):
            raise ValueError(f"Grounding reference {reference.get('id')} lacks effective_crystal_id")


def _relevance_for(identifier: str) -> str:
    if identifier == "DBA-08":
        return "Progressive Transformation constrains the object to minimum incremental capability."
    if identifier == "DBA-09":
        return "Transformation Lineage constrains provenance, grounding, and continuity references."
    if identifier == "DBA-10":
        return "Cognitive Orchestration constrains this step to non-orchestrating local instantiation."
    return "Retrieved governed DBA artefact."
