#!/usr/bin/env python3
"""Adaptive Engine: deterministic project-tier classification and risk ratchet.

Design goals (this docstring is the full write-up -- also see docs/ARCHITECTURE.md):

  * MAXIMUM CAPABILITY, MINIMUM ALWAYS-ON COST. Tiering exists to decide how
    much process a project needs, not to add process by default.
  * Deterministic and auditable. Given the same profile + risk answers, the
    same tier always comes out. No LLM call is involved in the computation.
  * Risk ratchet. Once a project has been classified at a given tier, later
    runs never silently drop below it. A downgrade requires an explicit,
    logged acknowledgement (`--acknowledge-downgrade "<reason>"`).
  * Stdlib only. Matches the rest of the package: no YAML/JSON-schema
    dependency. Risk answers are a small hand-editable JSON file.

This module is intentionally separate from lib/agent_workspace.py (which
still owns `profile()` — file/line/dependency scanning) so the "how big is
this repo" signal and the "how much rigor does this repo need" decision stay
independently testable and readable. agent_workspace.py imports and calls
into this module; it does not duplicate this logic.

Credit: the criticality x complexity -> tier scoring shape, and the
one-way risk-ratchet idea, are informed by the X-PRO project's public
tiering model (https://github.com/cdiegocom/xprodotai) as a design
reference. No code or file from that project is vendored or imported here
per the Ratchetry decision matrix (X-PRO's own repository
has zero stars/releases/CI and is not treated as a runtime dependency).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TIERS = ["T0", "T1", "T2", "T3"]

TIER_NAMES = {
    "T0": "Experiment / personal",
    "T1": "Standard project",
    "T2": "Product",
    "T3": "Critical / regulated system",
}

# Risk answers a human provides once and updates when facts change. Nothing
# here is inferred silently from source code, because these are exactly the
# facts static analysis cannot safely guess (who uses this, what data it
# touches, whether it's regulated).
DEFAULT_RISK_ANSWERS: dict[str, Any] = {
    "users": "internal",          # internal | external | public
    "handles_pii": False,
    "handles_payments": False,
    "life_safety": False,
    "regulated": False,           # explicit regulatory scope (HIPAA/PCI/SOX/GDPR-Art.9/etc.)
    "data_sensitivity": "internal",  # none | internal | confidential | restricted
    "external_exposure": False,   # reachable from the public internet
    # prototype | active | stable | legacy. Recorded and shown in tier.md for
    # human context (e.g. "this is a legacy system, be more careful"), but --
    # flagged via independent Codex cross-review (2026-08-30) -- it does NOT
    # currently feed criticality_score/complexity_score/compute_tier. It is
    # inert with respect to the actual tier computed; do not assume changing
    # it moves the tier.
    "maturity": "prototype",
}

# Weighted risk flags feeding the criticality score (0-15, uncapped input
# summed then clamped). Weights are deliberately coarse -- this is a routing
# signal, not a compliance certification.
_RISK_WEIGHTS: dict[str, int] = {
    "handles_pii": 3,
    "handles_payments": 4,
    "life_safety": 6,
    "regulated": 4,
    "external_exposure": 2,
}
_SENSITIVITY_WEIGHTS = {"none": 0, "internal": 1, "confidential": 3, "restricted": 5}
_USERS_WEIGHTS = {"internal": 0, "external": 2, "public": 4}

# Complexity score (0-8) derived from what profile() already computed, so we
# never re-walk the filesystem here.
_SIZE_COMPLEXITY = {"small": 0, "medium": 3, "large": 6}


def default_answers_path(project_root: Path) -> Path:
    return project_root / ".agents/state/risk-answers.json"


def load_risk_answers(project_root: Path) -> dict[str, Any]:
    path = default_answers_path(project_root)
    if not path.exists():
        return dict(DEFAULT_RISK_ANSWERS)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Invalid risk answers: managed state must be a regular file")
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Invalid risk answers: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Invalid risk answers: expected a JSON object")
    unknown = sorted(set(data) - set(DEFAULT_RISK_ANSWERS))
    if unknown:
        raise ValueError(f"Invalid risk answers: unknown field(s): {', '.join(unknown)}")
    for key in ["handles_pii", "handles_payments", "life_safety", "regulated", "external_exposure"]:
        if key in data and not isinstance(data[key], bool):
            raise ValueError(f"Invalid risk answers: {key} must be true or false")
    enums = {
        "users": {"internal", "external", "public"},
        "data_sensitivity": {"none", "internal", "confidential", "restricted"},
        "maturity": {"prototype", "active", "stable", "legacy"},
    }
    for key, allowed in enums.items():
        if key in data and data[key] not in allowed:
            raise ValueError(f"Invalid risk answers: {key} must be one of {', '.join(sorted(allowed))}")
    merged = dict(DEFAULT_RISK_ANSWERS)
    merged.update(data)
    return merged


def save_risk_answers(project_root: Path, answers: dict[str, Any]) -> None:
    path = default_answers_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULT_RISK_ANSWERS)
    merged.update({k: v for k, v in answers.items() if k in DEFAULT_RISK_ANSWERS})
    # Reuse the same schema checks as reads before persisting. A temporary
    # object keeps validation independent from any previous on-disk content.
    unknown = sorted(set(answers) - set(DEFAULT_RISK_ANSWERS))
    if unknown:
        raise ValueError(f"Invalid risk answers: unknown field(s): {', '.join(unknown)}")
    for key in ["handles_pii", "handles_payments", "life_safety", "regulated", "external_exposure"]:
        if not isinstance(merged[key], bool):
            raise ValueError(f"Invalid risk answers: {key} must be true or false")
    enums = {
        "users": {"internal", "external", "public"},
        "data_sensitivity": {"none", "internal", "confidential", "restricted"},
        "maturity": {"prototype", "active", "stable", "legacy"},
    }
    for key, allowed in enums.items():
        if merged[key] not in allowed:
            raise ValueError(f"Invalid risk answers: {key} must be one of {', '.join(sorted(allowed))}")
    path.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n")


def criticality_score(answers: dict[str, Any]) -> int:
    score = 0
    for key, weight in _RISK_WEIGHTS.items():
        if answers.get(key):
            score += weight
    score += _SENSITIVITY_WEIGHTS.get(answers.get("data_sensitivity", "internal"), 1)
    score += _USERS_WEIGHTS.get(answers.get("users", "internal"), 0)
    return min(score, 15)


def complexity_score(profile_data: dict[str, Any]) -> int:
    score = _SIZE_COMPLEXITY.get(profile_data.get("size", "small"), 0)
    if profile_data.get("monorepo"):
        score += 2
    score += min(len(profile_data.get("package_roots", [])), 4) // 2
    return min(score, 8)


def _base_tier(criticality: int, complexity: int) -> str:
    """Deterministic table lookup: criticality dominates, complexity breaks ties.

    This is intentionally a plain table rather than a formula: every cell is
    independently reviewable and the boundaries are the artifact under
    version control (this function's own diff), not a hidden constant.
    """
    if criticality >= 10:
        return "T3"
    if criticality >= 6:
        return "T2" if complexity < 6 else "T3"
    if criticality >= 3:
        return "T1" if complexity < 6 else "T2"
    # criticality 0-2: purely complexity-driven
    if complexity >= 6:
        return "T2"
    if complexity >= 3:
        return "T1"
    return "T0"


# Hard floors: some individual risk facts are non-negotiable regardless of
# the weighted total, because a single unmitigated fact here (e.g. handling
# payment data) is disqualifying at low rigor by itself.
_HARD_FLOORS: dict[str, str] = {
    "life_safety": "T3",
    "regulated": "T2",
    # Bug found via independent Codex cross-review (2026-08-30): this
    # docstring already claimed "handling payment data is disqualifying at
    # low rigor by itself", but handles_payments was never actually listed
    # here -- a small, purely internal project that merely handles payments
    # computed T1. Financial-correctness bugs are costly regardless of
    # exposure, so this floor applies unconditionally, not only combined
    # with external_exposure (see the now-redundant-but-harmless combined
    # rule below, kept for explicitness).
    "handles_payments": "T2",
}


def compute_tier(profile_data: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    crit = criticality_score(answers)
    comp = complexity_score(profile_data)
    tier = _base_tier(crit, comp)
    floor_reasons: list[str] = []
    for key, floor in _HARD_FLOORS.items():
        if answers.get(key) and TIERS.index(floor) > TIERS.index(tier):
            tier = floor
            floor_reasons.append(f"{key}=true forces minimum {floor}")
    if answers.get("handles_payments") and answers.get("external_exposure") and TIERS.index(tier) < TIERS.index("T2"):
        tier = "T2"
        floor_reasons.append("handles_payments + external_exposure forces minimum T2")
    return {
        "computed_tier": tier,
        "criticality_score": crit,
        "complexity_score": comp,
        "floor_reasons": floor_reasons,
    }


def history_path(project_root: Path) -> Path:
    return project_root / ".agents/state/tier-history.jsonl"


def read_history(project_root: Path) -> list[dict[str, Any]]:
    path = history_path(project_root)
    if not path.exists():
        return []
    if path.is_symlink() or not path.is_file():
        raise ValueError("Invalid tier history: managed state must be a regular file")
    out = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid tier history at line {line_number}: {exc}") from exc
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid tier history at line {line_number}: expected a JSON object")
        for field in ["computed_tier", "effective_tier"]:
            if entry.get(field) not in TIERS:
                raise ValueError(f"Invalid tier history at line {line_number}: {field} is not a known tier")
        acknowledged = entry.get("downgrade_acknowledged", False)
        if not isinstance(acknowledged, bool):
            raise ValueError(f"Invalid tier history at line {line_number}: downgrade_acknowledged must be boolean")
        reason = entry.get("downgrade_reason")
        computed = entry["computed_tier"]
        effective = entry["effective_tier"]
        ratcheted = entry.get("ratcheted", False)
        if not isinstance(ratcheted, bool):
            raise ValueError(f"Invalid tier history at line {line_number}: ratcheted must be boolean")
        if acknowledged:
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(
                    f"Invalid tier history at line {line_number}: an acknowledged downgrade requires a rationale"
                )
            if effective != computed or ratcheted:
                raise ValueError(
                    f"Invalid tier history at line {line_number}: an acknowledged downgrade must reset to the computed tier"
                )
        elif reason is not None:
            raise ValueError(
                f"Invalid tier history at line {line_number}: downgrade_reason requires downgrade_acknowledged=true"
            )
        if TIERS.index(effective) < TIERS.index(computed):
            raise ValueError(
                f"Invalid tier history at line {line_number}: effective_tier cannot be lower than computed_tier"
            )
        expected_ratcheted = TIERS.index(effective) > TIERS.index(computed)
        if ratcheted != expected_ratcheted:
            raise ValueError(
                f"Invalid tier history at line {line_number}: ratcheted does not match computed/effective tiers"
            )
        out.append(entry)
    return out


def highest_recorded_tier(project_root: Path) -> str | None:
    # An acknowledged downgrade resets the ratchet floor: only look at history
    # entries from the most recent such acknowledgement onward. Without this,
    # the floor is computed over the *entire* append-only log forever, so an
    # acknowledged downgrade would only ever apply to the one run that made
    # it -- the very next ordinary run would find the old, higher tier still
    # sitting in history and silently ratchet back up to it.
    history = read_history(project_root)
    last_reset = None
    for i, entry in enumerate(history):
        if entry.get("downgrade_acknowledged"):
            last_reset = i
    relevant = history[last_reset:] if last_reset is not None else history
    tiers = [entry.get("effective_tier") for entry in relevant if entry.get("effective_tier") in TIERS]
    if not tiers:
        return None
    return max(tiers, key=TIERS.index)


def acknowledged_downgrade(project_root: Path) -> dict[str, Any] | None:
    """Describe the most recent acknowledged downgrade, if there is one.

    :func:`highest_recorded_tier` deliberately forgets everything before the
    last acknowledgement so the ratchet floor resets. That reset is right for
    *computing* a tier and wrong for *reporting* one: without this function an
    acknowledgement is visible only in the run that made it, and every later
    `tier`/`doctor` run presents a downgraded project as an ordinary one. A
    setting that is weak but legal has to keep announcing itself, otherwise it
    becomes the silent default -- so callers surface this for as long as the
    project still sits below the tier it was downgraded from.

    Returns None when no acknowledgement was ever recorded, otherwise
    ``{"timestamp", "reason", "from_tier", "to_tier"}`` where ``from_tier`` is
    the highest tier recorded before the acknowledgement. Deciding whether the
    downgrade still *stands* is the caller's job: compare the project's current
    effective tier against ``from_tier``, since a project that has since been
    reclassified back up is no longer operating below its recorded history.
    """
    history = read_history(project_root)
    last_reset = None
    for i, entry in enumerate(history):
        if entry.get("downgrade_acknowledged"):
            last_reset = i
    if last_reset is None:
        return None
    entry = history[last_reset]
    prior = [
        e.get("effective_tier")
        for e in history[:last_reset]
        if e.get("effective_tier") in TIERS
    ]
    if not prior:
        return None
    from_tier = max(prior, key=TIERS.index)
    to_tier = entry["effective_tier"]
    if TIERS.index(from_tier) <= TIERS.index(to_tier):
        return None
    return {
        "timestamp": entry.get("timestamp"),
        "reason": entry.get("downgrade_reason"),
        "from_tier": from_tier,
        "to_tier": to_tier,
    }


def downgrade_notice(project_root: Path, effective_tier: str) -> str | None:
    """One-line, human-readable standing-downgrade notice, or None.

    Shared by `tier.md` rendering and `doctor` so both report the same fact in
    the same words instead of drifting apart.
    """
    ack = acknowledged_downgrade(project_root)
    if not ack or effective_tier not in TIERS:
        return None
    if TIERS.index(effective_tier) >= TIERS.index(ack["from_tier"]):
        return None
    when = (ack.get("timestamp") or "an earlier run").split("T")[0]
    reason = ack.get("reason") or "no rationale recorded"
    return (
        f"Tier {effective_tier} stands below the previously recorded "
        f"{ack['from_tier']}, downgraded on {when}: \"{reason}\". This is an "
        "acknowledged decision, not an error -- re-run `ratchery tier` "
        "after the risk facts change."
    )


def evaluate_tier(project_root: Path, profile_data: dict[str, Any]) -> dict[str, Any]:
    """Compute the tier and current ratchet result without writing state.

    This is the read-only counterpart to :func:`classify`. Diagnostics and CI
    use it to derive every security-relevant tier field from risk answers,
    project facts, and ratchet history instead of trusting editable derived
    fields in ``tier.json``.
    """
    result = compute_tier(profile_data, load_risk_answers(project_root))
    computed = result["computed_tier"]
    prior_high = highest_recorded_tier(project_root)
    effective = computed
    ratcheted = False
    if prior_high and TIERS.index(prior_high) > TIERS.index(computed):
        effective = prior_high
        ratcheted = True
    return {
        **result,
        "effective_tier": effective,
        "ratcheted": ratcheted,
        "tier_name": TIER_NAMES[effective],
        "requirements": tier_requirements(effective),
    }


def append_history(project_root: Path, entry: dict[str, Any]) -> None:
    path = history_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def classify(
    project_root: Path,
    profile_data: dict[str, Any],
    acknowledge_downgrade: str | None = None,
) -> dict[str, Any]:
    """Compute this run's tier and apply the risk ratchet.

    Returns a dict with `computed_tier` (what the scoring says today),
    `effective_tier` (what actually applies, after the ratchet), and
    `ratcheted` (True if effective_tier was raised above computed_tier
    because of prior history).

    `acknowledge_downgrade`, when set to a non-empty rationale string,
    resets the ratchet floor to the newly computed tier, and that
    acknowledgement is itself durably logged -- the ratchet is auditable,
    not bypassable-without-a-trace.
    """
    if acknowledge_downgrade is not None and not acknowledge_downgrade.strip():
        raise ValueError("Downgrade acknowledgement requires a non-empty rationale")
    evaluated = evaluate_tier(project_root, profile_data)
    computed = evaluated["computed_tier"]
    effective = evaluated["effective_tier"]
    ratcheted = evaluated["ratcheted"]
    downgrade_acknowledged = False
    if ratcheted and acknowledge_downgrade:
        effective = computed
        ratcheted = False
        downgrade_acknowledged = True

    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "computed_tier": computed,
        "effective_tier": effective,
        "criticality_score": evaluated["criticality_score"],
        "complexity_score": evaluated["complexity_score"],
        "floor_reasons": evaluated["floor_reasons"],
        "ratcheted": ratcheted,
        "downgrade_acknowledged": downgrade_acknowledged,
        "downgrade_reason": acknowledge_downgrade.strip() if downgrade_acknowledged else None,
    }
    append_history(project_root, entry)

    out = dict(entry)
    out["tier_name"] = TIER_NAMES[effective]
    out["requirements"] = tier_requirements(effective)
    write_tier_state(project_root, out)
    return out


def tier_state_path(project_root: Path) -> Path:
    return project_root / ".agents/state/tier.json"


def write_tier_state(project_root: Path, state: dict[str, Any]) -> None:
    tier_state_path(project_root).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    md_path = project_root / ".agents/state/tier.md"
    req = state["requirements"]
    lines = [
        "# Project Tier",
        "",
        f"- Effective tier: **{state['effective_tier']}** ({state['tier_name']})",
        f"- Computed tier this run: {state['computed_tier']}",
        f"- Criticality score: {state['criticality_score']}/15",
        f"- Complexity score: {state['complexity_score']}/8",
    ]
    if state.get("ratcheted"):
        lines.append(
            "- ⚠️ Ratcheted: this run computed a lower tier, but the project was previously "
            f"classified at {state['effective_tier']}. Rigor was not silently reduced. "
            "Use `ratchery tier --acknowledge-downgrade \"<reason>\"` to accept a lower tier."
        )
    notice = downgrade_notice(project_root, state["effective_tier"])
    if notice:
        lines.append(f"- \u26a0\ufe0f {notice}")
    if state.get("floor_reasons"):
        lines.append("- Hard floors applied: " + "; ".join(state["floor_reasons"]))
    lines += [
        "",
        "## Requirements at this tier",
        "",
        f"- Spec mode: {req['spec_mode']}",
        f"- Required docs: {', '.join(req['required_docs']) or 'none beyond baseline'}",
        f"- Required agents: {', '.join(req['required_agents']) or 'none beyond core'}",
        f"- Required skills: {', '.join(req['required_skills']) or 'none beyond global'}",
        f"- Testing bar: {req['testing_bar']}",
        f"- Security bar: {req['security_bar']}",
        "",
        "This file is regenerated by `ratchery tier`. Do not hand-edit; "
        "edit `.agents/state/risk-answers.json` and re-run instead.",
    ]
    md_path.write_text("\n".join(lines) + "\n")


def resolve_active_agents(registry: dict[str, Any], effective_tier: str, capabilities: dict[str, bool]) -> dict[str, str]:
    """Given the agent registry (assets/global/skills/registry.json), the
    project's effective tier, and its detected capabilities, return
    {agent_name: reason} for every specialized/optimization/operations agent
    that should actually be installed into this project right now.

    This is the enforcement half of what registry.json used to only
    describe: without it, every agent file shipped unconditionally to every
    project regardless of tier or relevance, which directly contradicted
    the "maximum capability, minimum always-on cost" principle. The four
    original baseline agents (explorer, reviewer, security-reviewer,
    test-runner) are intentionally NOT decided here -- they stay
    unconditionally installed by the caller for backward compatibility,
    matching the pre-v1.0 behavior and the existing test suite.

    'on-demand' agents are deliberately excluded from the result: they are
    never auto-installed, only enabled explicitly via
    `ratchery agents enable <name>`.
    """
    active: dict[str, str] = {}
    for name, meta in registry.get("agents", {}).items():
        activation = meta.get("activation")
        if activation == "tier-gated":
            floor = meta.get("activates_at_tier", "T0")
            if floor in TIERS and TIERS.index(effective_tier) >= TIERS.index(floor):
                active[name] = f"tier-gated at {floor}; project is {effective_tier}"
        elif activation == "conditional":
            cap = meta.get("trigger_capability")
            if cap and capabilities.get(cap):
                active[name] = f"capability '{cap}' detected"
        # 'on-demand' and any unrecognized activation model are never auto-installed.
    return active


def tier_requirements(tier: str) -> dict[str, Any]:
    """What a given tier requires. Consumed by the agent/skill loader and by
    `ratchery doctor` to check a project isn't under-equipped for its
    own recorded tier. This is data, not enforcement by itself -- callers
    decide what to do when a requirement isn't met (warn vs. block)."""
    base = {
        "spec_mode": "none",
        "required_docs": [],
        "required_agents": [],
        "required_skills": [],
        "testing_bar": "none required",
        "security_bar": "sandbox + secondary hook (framework default)",
    }
    if tier == "T0":
        return base
    if tier == "T1":
        return {
            **base,
            "spec_mode": "openspec-light",
            "required_docs": ["docs/PROJECT_CONTEXT.md"],
            "testing_bar": "smoke tests for changed behavior",
        }
    if tier == "T2":
        return {
            **base,
            "spec_mode": "openspec-light",
            "required_docs": ["docs/PROJECT_CONTEXT.md", "docs/decisions/"],
            "required_agents": ["architect", "security-reviewer"],
            "required_skills": ["security-scan", "dependency-audit"],
            "testing_bar": "unit + integration tests for changed behavior, CI required",
            "security_bar": "sandbox + secondary hook + security-reviewer agent on risk-relevant changes",
        }
    if tier == "T3":
        return {
            **base,
            "spec_mode": "speckit-full",
            "required_docs": ["docs/PROJECT_CONTEXT.md", "docs/decisions/", "docs/SECURITY_REVIEW.md"],
            "required_agents": ["architect", "security-reviewer", "qa"],
            "required_skills": ["security-scan", "dependency-audit", "architecture-map"],
            "testing_bar": "unit + integration + regression tests required, CI required, human review before merge",
            "security_bar": "sandbox + secondary hook + mandatory security-reviewer sign-off + CodeGuard rules (if installed)",
        }
    return base
