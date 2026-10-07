"""Offline capability catalog, behavioral evals, workflows, and technology radar.

The module deliberately performs no network access and no project mutation.  It turns
Ratchetry's shipped declarative assets into inspectable contracts that both clients can
share without making either client the source of truth.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any


KINDS = {"agent", "skill"}
CLIENTS = {"claude", "codex"}
NETWORK_POLICIES = {"none", "task-explicit"}
PERMISSION_CEILINGS = {"read-only", "project-edit", "security-gated"}
RADAR_DECISIONS = {"adopted", "trial", "assess", "hold"}
RADAR_STATUSES = {"active", "preview", "deprecated"}
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
RADAR_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\n(?P<header>.*?)\n---(?:\n|\Z)", re.DOTALL)


class CapabilityError(ValueError):
    """Raised when a shipped declarative contract is malformed."""


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CapabilityError(f"Cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CapabilityError(f"Expected a JSON object in {path}")
    return value


def _safe_asset(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise CapabilityError(f"Unsafe asset path: {relative!r}")
    root = root.resolve()
    candidate = root / relative
    if candidate.is_symlink():
        raise CapabilityError(f"Shipped asset must not be a symlink: {relative}")
    try:
        candidate.resolve().relative_to(root)
    except (OSError, ValueError) as exc:
        raise CapabilityError(f"Asset escapes package root: {relative}") from exc
    return candidate


def _digest(root: Path, sources: list[Path]) -> str:
    digest = hashlib.sha256()
    files: list[Path] = []
    for source in sources:
        if source.is_symlink():
            raise CapabilityError(
                f"Shipped capability source must not be a symlink: {source}"
            )
        if source.is_dir():
            files.extend(path for path in source.rglob("*") if path.is_file())
        elif source.is_file():
            files.append(source)
        else:
            raise CapabilityError(f"Missing capability source: {source}")
    for path in sorted(files):
        if path.is_symlink():
            raise CapabilityError(
                f"Shipped capability resource must not be a symlink: {path}"
            )
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text()
    except OSError as exc:
        raise CapabilityError(f"Cannot read {path}: {exc}") from exc
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise CapabilityError(f"Missing YAML frontmatter in {path}")
    values: dict[str, str] = {}
    for line in match.group("header").splitlines():
        key, separator, raw = line.partition(":")
        if separator:
            values[key.strip()] = raw.strip().strip('"')
    return values


def _registry(root: Path) -> dict[str, Any]:
    return _load_object(root / "assets/global/skills/registry.json")


def _metadata(registry: dict[str, Any], kind: str, name: str) -> dict[str, Any]:
    metadata = registry.get("metadata")
    if not isinstance(metadata, dict):
        raise CapabilityError("Capability registry is missing metadata")
    defaults = metadata.get("defaults")
    catalog = metadata.get(f"{kind}s")
    if not isinstance(defaults, dict) or not isinstance(catalog, dict):
        raise CapabilityError("Capability registry metadata must define defaults/catalogs")
    item = catalog.get(name)
    if not isinstance(item, dict):
        raise CapabilityError(f"Missing {kind} metadata: {name}")
    return {**defaults, **item}


def _skill_names(registry: dict[str, Any]) -> list[str]:
    skills = registry.get("skills")
    available = skills.get("available") if isinstance(skills, dict) else None
    if not isinstance(available, list) or not all(
        isinstance(name, str) and name for name in available
    ):
        raise CapabilityError("Registry skills.available must be a list of names")
    return available


def _agent_names(registry: dict[str, Any]) -> list[str]:
    agents = registry.get("agents")
    if not isinstance(agents, dict):
        raise CapabilityError("Registry agents must be an object")
    return list(agents)


def capability_names(root: Path, kind: str) -> list[str]:
    if kind not in KINDS:
        raise CapabilityError(f"Unknown capability kind: {kind}")
    registry = _registry(root)
    names = _skill_names(registry) if kind == "skill" else _agent_names(registry)
    return sorted(names)


def capability_detail(root: Path, kind: str, name: str) -> dict[str, Any]:
    if name not in capability_names(root, kind):
        raise CapabilityError(f"Unknown {kind}: {name}")
    registry = _registry(root)
    meta = _metadata(registry, kind, name)
    if kind == "skill":
        directory = _safe_asset(root, f"assets/global/skills/{name}")
        contract = _frontmatter(directory / "SKILL.md")
        sources = [directory]
        source_names = [directory.relative_to(root).as_posix()]
        client_contracts = {
            "claude": f"~/.claude/skills/{name}/SKILL.md",
            "codex": f"~/.agents/skills/{name}/SKILL.md",
        }
        declared_names = {"skill": contract.get("name")}
    else:
        claude = _safe_asset(root, f"assets/project/.claude/agents/{name}.md")
        codex = _safe_asset(
            root, f"assets/project/.codex/agents/{name.replace('-', '_')}.toml"
        )
        contract = _frontmatter(claude)
        try:
            codex_data = tomllib.loads(codex.read_text())
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise CapabilityError(f"Cannot parse {codex}: {exc}") from exc
        sources = [claude, codex]
        source_names = [path.relative_to(root).as_posix() for path in sources]
        client_contracts = {
            "claude": {
                "path": source_names[0],
                "permission_mode": contract.get("permissionMode", "default"),
                "tools": [
                    item.strip()
                    for item in contract.get("tools", "").split(",")
                    if item.strip()
                ],
            },
            "codex": {
                "path": source_names[1],
                "default_permissions": codex_data.get("default_permissions"),
            },
        }
        declared_names = {
            "claude": contract.get("name"),
            "codex": codex_data.get("name"),
        }
    return {
        "kind": kind,
        "name": name,
        "version": meta.get("version"),
        "origin": meta.get("origin"),
        "description": contract.get("description", ""),
        "clients": meta.get("clients"),
        "permission_ceiling": meta.get("permission_ceiling"),
        "network": meta.get("network"),
        "signals": meta.get("signals"),
        "anti_signals": meta.get("anti_signals"),
        "evals": meta.get("evals"),
        "sources": source_names,
        "resources": sorted(
            path.relative_to(root).as_posix()
            for source in sources
            for path in ([source] if source.is_file() else source.rglob("*"))
            if path.is_file()
        ),
        "digest": _digest(root, sources),
        "client_contracts": client_contracts,
        "declared_names": declared_names,
    }


def list_capabilities(root: Path, kind: str) -> list[dict[str, Any]]:
    return [capability_detail(root, kind, name) for name in capability_names(root, kind)]


def _normalized(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def recommend_capabilities(root: Path, kind: str, request: str) -> list[dict[str, Any]]:
    text = _normalized(request)
    matches: list[dict[str, Any]] = []
    for detail in list_capabilities(root, kind):
        anti_matches = [
            phrase
            for phrase in detail["anti_signals"]
            if _normalized(phrase) in text
        ]
        if anti_matches:
            continue
        signal_matches = [
            phrase
            for phrase in detail["signals"]
            if _normalized(phrase) in text
        ]
        if not signal_matches:
            continue
        score = sum(max(1, len(_normalized(phrase).split())) for phrase in signal_matches)
        matches.append(
            {
                "name": detail["name"],
                "score": score,
                "matched_signals": signal_matches,
            }
        )
    return sorted(matches, key=lambda item: (-item["score"], item["name"]))


def _evals(root: Path) -> dict[str, Any]:
    return _load_object(root / "assets/global/evals/capability-routing.json")


def run_capability_evals(root: Path, kind: str) -> dict[str, Any]:
    if kind not in KINDS:
        raise CapabilityError(f"Unknown capability kind: {kind}")
    cases = _evals(root).get("cases")
    if not isinstance(cases, list):
        raise CapabilityError("Capability eval registry must contain cases")
    results = []
    for case in cases:
        if not isinstance(case, dict) or case.get("kind") != kind:
            continue
        selected = [
            item["name"]
            for item in recommend_capabilities(root, kind, str(case.get("input", "")))
        ]
        expected = case.get("expected", [])
        forbidden = case.get("forbidden", [])
        missing = [name for name in expected if name not in selected]
        unexpected = [name for name in forbidden if name in selected]
        results.append(
            {
                "id": case.get("id"),
                "passed": not missing and not unexpected,
                "selected": selected,
                "missing": missing,
                "unexpected": unexpected,
            }
        )
    return {
        "kind": kind,
        "passed": all(item["passed"] for item in results),
        "total": len(results),
        "failed": sum(not item["passed"] for item in results),
        "results": results,
    }


def validate_capabilities(root: Path, kind: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    counts: dict[str, int] = {}
    kinds = [kind] if kind else sorted(KINDS)
    if any(item not in KINDS for item in kinds):
        raise CapabilityError(f"Unknown capability kind: {kind}")
    try:
        registry = _registry(root)
        if not str(registry.get("schema_version", "")).startswith("2."):
            errors.append("Capability registry schema_version must be 2.x")
        metadata = registry.get("metadata", {})
        for current_kind in kinds:
            names = capability_names(root, current_kind)
            counts[current_kind] = len(names)
            catalog = metadata.get(f"{current_kind}s", {})
            if set(names) != set(catalog):
                errors.append(
                    f"{current_kind} metadata mismatch: inventory={sorted(names)}, "
                    f"catalog={sorted(catalog) if isinstance(catalog, dict) else 'invalid'}"
                )
                continue
            for name in names:
                try:
                    detail = capability_detail(root, current_kind, name)
                except CapabilityError as exc:
                    errors.append(str(exc))
                    continue
                if not SEMVER_RE.fullmatch(str(detail["version"] or "")):
                    errors.append(f"{current_kind} {name}: version must be semver")
                if set(detail["clients"] or []) != CLIENTS:
                    errors.append(f"{current_kind} {name}: clients must cover Claude and Codex")
                if any(
                    not isinstance(declared_name, str)
                    or declared_name.replace("_", "-") != name
                    for declared_name in detail["declared_names"].values()
                ):
                    errors.append(
                        f"{current_kind} {name}: declared names do not match registry: "
                        f"{detail['declared_names']}"
                    )
                if detail["network"] not in NETWORK_POLICIES:
                    errors.append(f"{current_kind} {name}: invalid network policy")
                if detail["permission_ceiling"] not in PERMISSION_CEILINGS:
                    errors.append(f"{current_kind} {name}: invalid permission ceiling")
                for field in ("signals", "anti_signals", "evals"):
                    values = detail[field]
                    if not isinstance(values, list) or not all(
                        isinstance(value, str) and value for value in values
                    ):
                        errors.append(f"{current_kind} {name}: {field} must be strings")
                if not detail["signals"]:
                    errors.append(f"{current_kind} {name}: at least one signal is required")
                if current_kind == "agent":
                    claude_contract = detail["client_contracts"]["claude"]
                    codex_contract = detail["client_contracts"]["codex"]
                    editing_tools = {"Edit", "Write"} & set(
                        claude_contract["tools"]
                    )
                    if detail["permission_ceiling"] == "read-only":
                        if editing_tools or codex_contract["default_permissions"] != ":read-only":
                            errors.append(
                                f"agent {name}: native permissions exceed read-only metadata"
                            )
                    elif not editing_tools or codex_contract["default_permissions"] != "project-edit":
                        errors.append(
                            f"agent {name}: native edit permissions do not match metadata"
                        )
        eval_data = _evals(root)
        cases = eval_data.get("cases")
        if not str(eval_data.get("schema_version", "")).startswith("1."):
            errors.append("Capability eval schema_version must be 1.x")
        if not isinstance(cases, list):
            errors.append("Capability eval cases must be a list")
        else:
            ids: set[str] = set()
            registry_eval_ids = {
                eval_id
                for current_kind in kinds
                for name in capability_names(root, current_kind)
                for eval_id in _metadata(registry, current_kind, name).get("evals", [])
            }
            for case in cases:
                if not isinstance(case, dict):
                    errors.append("Capability eval case must be an object")
                    continue
                case_id = case.get("id")
                if not isinstance(case_id, str) or not case_id:
                    errors.append("Capability eval case is missing an id")
                    continue
                if case_id in ids:
                    errors.append(f"Duplicate capability eval id: {case_id}")
                ids.add(case_id)
                case_kind = case.get("kind")
                if case_kind not in KINDS:
                    errors.append(f"Eval {case_id}: invalid kind")
                    continue
                known = set(capability_names(root, case_kind))
                for field in ("expected", "forbidden"):
                    values = case.get(field)
                    if not isinstance(values, list) or not set(values) <= known:
                        errors.append(f"Eval {case_id}: invalid {field} capabilities")
            missing_evals = registry_eval_ids - ids
            if missing_evals:
                errors.append(f"Missing registered eval cases: {sorted(missing_evals)}")
        for current_kind in kinds:
            result = run_capability_evals(root, current_kind)
            if not result["passed"]:
                failed = [item["id"] for item in result["results"] if not item["passed"]]
                errors.append(f"{current_kind} behavior eval failures: {failed}")
            if result["total"] == 0:
                warnings.append(f"No {current_kind} behavior evals are registered")
    except CapabilityError as exc:
        errors.append(str(exc))
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": counts,
    }


def _workflows(root: Path) -> dict[str, Any]:
    return _load_object(root / "assets/global/workflows/registry.json")


def validate_workflows(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    data = _workflows(root)
    workflows = data.get("workflows")
    if not str(data.get("schema_version", "")).startswith("1."):
        errors.append("Workflow schema_version must be 1.x")
    if not isinstance(workflows, list):
        return {"ok": False, "errors": ["Workflow registry must contain workflows"]}
    ids: set[str] = set()
    known = {
        kind: set(capability_names(root, kind)) for kind in KINDS
    }
    for workflow in workflows:
        if not isinstance(workflow, dict):
            errors.append("Workflow entry must be an object")
            continue
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, str) or not workflow_id:
            errors.append("Workflow entry is missing an id")
            continue
        if workflow_id in ids:
            errors.append(f"Duplicate workflow id: {workflow_id}")
        ids.add(workflow_id)
        if not workflow.get("signals") or not isinstance(workflow.get("steps"), list):
            errors.append(f"Workflow {workflow_id}: signals and steps are required")
        approval_gate = False
        for step in workflow.get("steps", []):
            if not isinstance(step, dict):
                errors.append(f"Workflow {workflow_id}: step must be an object")
                continue
            approval_gate = approval_gate or step.get("type") == "approval"
            for ref in step.get("capabilities", []):
                if not isinstance(ref, str) or ":" not in ref:
                    errors.append(f"Workflow {workflow_id}: invalid capability {ref!r}")
                    continue
                ref_kind, ref_name = ref.split(":", 1)
                if ref_kind not in known or ref_name not in known[ref_kind]:
                    errors.append(f"Workflow {workflow_id}: unknown capability {ref}")
        if workflow.get("requires_approval") and not approval_gate:
            errors.append(f"Workflow {workflow_id}: declared approval gate is missing")
    return {"ok": not errors, "errors": errors, "count": len(workflows)}


def list_workflows(root: Path) -> list[dict[str, Any]]:
    result = validate_workflows(root)
    if not result["ok"]:
        raise CapabilityError("; ".join(result["errors"]))
    return sorted(_workflows(root)["workflows"], key=lambda item: item["id"])


def workflow_detail(root: Path, workflow_id: str) -> dict[str, Any]:
    for workflow in list_workflows(root):
        if workflow["id"] == workflow_id:
            return workflow
    raise CapabilityError(f"Unknown workflow: {workflow_id}")


def recommend_workflows(root: Path, goal: str) -> list[dict[str, Any]]:
    text = _normalized(goal)
    matches = []
    for workflow in list_workflows(root):
        signals = [
            signal
            for signal in workflow["signals"]
            if _normalized(signal) in text
        ]
        if signals:
            matches.append(
                {
                    "id": workflow["id"],
                    "title": workflow["title"],
                    "score": sum(len(_normalized(signal).split()) for signal in signals),
                    "matched_signals": signals,
                    "mutates": workflow["mutates"],
                    "requires_approval": workflow["requires_approval"],
                }
            )
    return sorted(matches, key=lambda item: (-item["score"], item["id"]))


def _radar(root: Path) -> dict[str, Any]:
    return _load_object(root / "assets/global/technology-radar.json")


def validate_radar(root: Path, today: dt.date | None = None) -> dict[str, Any]:
    today = today or dt.date.today()
    errors: list[str] = []
    entries = _radar(root).get("entries")
    if not isinstance(entries, list):
        return {"ok": False, "errors": ["Technology radar must contain entries"]}
    ids: set[str] = set()
    stale: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("Technology radar entry must be an object")
            continue
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id:
            errors.append("Technology radar entry is missing an id")
            continue
        if not RADAR_ID_RE.fullmatch(entry_id):
            errors.append(f"Radar {entry_id!r}: id must be lowercase kebab-case")
            continue
        if entry_id in ids:
            errors.append(f"Duplicate technology radar id: {entry_id}")
        ids.add(entry_id)
        if entry.get("decision") not in RADAR_DECISIONS:
            errors.append(f"Radar {entry_id}: invalid decision")
        if entry.get("status") not in RADAR_STATUSES:
            errors.append(f"Radar {entry_id}: invalid status")
        if not str(entry.get("url", "")).startswith("https://"):
            errors.append(f"Radar {entry_id}: URL must use HTTPS")
        try:
            reviewed = dt.date.fromisoformat(entry["last_reviewed"])
            recheck = dt.date.fromisoformat(entry["recheck_by"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"Radar {entry_id}: invalid review dates")
            continue
        if recheck < reviewed:
            errors.append(f"Radar {entry_id}: recheck precedes last review")
        if recheck < today:
            stale.append(entry_id)
    return {
        "ok": not errors,
        "errors": errors,
        "count": len(entries),
        "stale": sorted(stale),
        "as_of": today.isoformat(),
    }


def list_radar(root: Path, today: dt.date | None = None) -> list[dict[str, Any]]:
    validation = validate_radar(root, today)
    if not validation["ok"]:
        raise CapabilityError("; ".join(validation["errors"]))
    stale = set(validation["stale"])
    return sorted(
        [
            {**entry, "stale": entry["id"] in stale}
            for entry in _radar(root)["entries"]
        ],
        key=lambda entry: entry["id"],
    )


def radar_detail(root: Path, entry_id: str, today: dt.date | None = None) -> dict[str, Any]:
    for entry in list_radar(root, today):
        if entry["id"] == entry_id:
            return entry
    raise CapabilityError(f"Unknown technology radar entry: {entry_id}")


def radar_summary(root: Path, today: dt.date | None = None) -> dict[str, Any]:
    entries = list_radar(root, today)
    decisions = {
        decision: sum(entry["decision"] == decision for entry in entries)
        for decision in sorted(RADAR_DECISIONS)
    }
    return {
        "count": len(entries),
        "decisions": decisions,
        "stale": [entry["id"] for entry in entries if entry["stale"]],
        "network_access": "none",
    }
