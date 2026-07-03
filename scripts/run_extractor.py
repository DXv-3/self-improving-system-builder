#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

REQUIRED_SECTIONS = [
    "name:", "version:", "description:", "core_thesis:", "when_to_use:",
    "inputs:", "outputs:", "workflow:", "mistakes_to_avoid:", "hard_stop_conditions:",
]

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").strip()

def reconstruct_arc(text: str) -> dict:
    lower = text.lower()
    pivots = []
    if "github" in lower or "repo" in lower:
        pivots.append("conversation pivoted into repo delivery")
    if "skill.md" in lower or "skill file" in lower:
        pivots.append("conversation pivoted into skill extraction")
    if "test" in lower or "pytest" in lower:
        pivots.append("conversation pivoted into proof and verification")
    if "roadmap" in lower:
        pivots.append("conversation pivoted into preserving unbuilt work")
    actual_problem = (
        "build a self-improving, self-healing system and preserve it as reusable skills"
        if "self-improving" in lower
        else "extract the highest-leverage reusable capability from the conversation"
    )
    artifacts: set[str] = set()
    for pat in [r"[\w\-/]+\.py", r"[\w\-/]+\.md", r"[\w\-/]+\.json", r"[\w\-/]+\.yml"]:
        artifacts.update(re.findall(pat, text))
    return {
        "start": "User wanted continuation and preservation of prior work.",
        "actual_problem": actual_problem,
        "pivots": pivots or ["conversation iterated toward higher-leverage packaging"],
        "artifacts": sorted(artifacts)[:100],
        "optimization_target": "maximum reuse, exact preservation, runnable delivery, minimal information loss",
    }

def identify_candidate_skills(text: str) -> list[dict]:
    candidates = [
        {"name": "conversation-to-system-extractor", "kind": "meta", "score": 10},
        {"name": "self-improving-system-builder", "kind": "structural", "score": 9},
        {"name": "forward-executor", "kind": "workflow", "score": 8},
        {"name": "repo-healing-operator", "kind": "tooling", "score": 7},
    ]
    if "skill.md" not in text.lower():
        candidates = [c for c in candidates if c["name"] != "conversation-to-system-extractor"]
    return sorted(candidates, key=lambda x: (-x["score"], x["name"]))

def choose_packaging(candidates: list[dict]) -> str:
    if len(candidates) >= 2 and candidates[0]["score"] - candidates[1]["score"] <= 1:
        return "parent_plus_subskills"
    return "single_best_skill"

def preserve_gold(text: str) -> dict:
    exact_lines: list[str] = []
    tokens = [
        "runtime_proven", "compiler_inferred", "reference_only", "unverified", "contradicted",
        "RECONSTRUCT", "EVIDENCE_CLASSIFICATION", "IDKWIDK", "CODE_HARDENING",
        "FORWARD_EXECUTION", "PROOF", "REPO_DELIVERY", "score =", "risk_level <= 4",
        "WHAT WE BUILT", "WHAT WE DID NOT BUILD", "WHAT WILL BREAK",
    ]
    for line in text.splitlines():
        s = line.strip()
        if s and any(tok in s for tok in tokens):
            exact_lines.append(s)
    return {"exact_lines": exact_lines[:50]}

def emit_skill(name: str, arc: dict, gold: dict) -> str:
    descriptions = {
        "conversation-to-system-extractor": "Extract one or more reusable skills from a full conversation without losing the deeper pattern underneath the surface topic.",
        "self-improving-system-builder": "Build self-healing systems that detect blind spots, execute safe fixes, preserve learning, and prove progress across runs.",
        "forward-executor": "Turn findings into a scored action queue and execute everything safe before asking for human intervention.",
        "repo-healing-operator": "Inspect an in-progress repo, find real breakpoints, and patch the highest-leverage gaps first.",
    }
    cores = {
        "conversation-to-system-extractor": "The most valuable output from a conversation is usually the reusable operating manual hidden beneath the transcript.",
        "self-improving-system-builder": "A system is not self-improving until it can detect, execute, verify, persist, and re-trigger improvement loops automatically.",
        "forward-executor": "Execution is the plan; safe actions should be carried out immediately, not deferred into recommendations.",
        "repo-healing-operator": "The right next fix comes from tracing the actual execution chain, not from guessing.",
    }
    steps = [
        "Reconstruct the conversation arc or repo state.",
        "Identify the actual problem beneath the surface request.",
        "Enumerate candidate skills or fixes, including non-obvious ones.",
        "Choose the highest-leverage packaging or patch sequence.",
        "Preserve exact gold: formulas, schema names, thresholds, prompts, workflow labels.",
        "Produce runnable artifacts, not summaries.",
        "List what remains unbuilt with explicit next actions.",
    ]
    return "\n".join([
        f"name: {name}", "version: 1.0.0",
        f"description: {descriptions[name]}",
        f"core_thesis: {cores[name]}",
        "when_to_use:",
        "  - When a conversation contains reusable operating logic that should outlive the transcript.",
        "  - When the last topic is not necessarily the most valuable thing to package.",
        "inputs:", "  required:", "    - Full conversation transcript or repo state",
        "  optional:", "    - Existing files, tests, roadmap, prior skill files",
        "outputs:",
        "  - One or more complete skill.md files",
        "  - Optional supporting manifests, patch notes, or continuation files",
        "workflow:", *[f"  - {s}" for s in steps],
        "mistakes_to_avoid:",
        "  - Summarizing instead of writing an operating manual",
        "  - Capturing only the final topic",
        "  - Paraphrasing away exact formulas or schema fields",
        "  - Stopping before generating runnable artifacts",
        "hard_stop_conditions:",
        "  - A future agent reading only the output can continue the work without the original transcript",
        "preserved_gold:", *[f"  - {l}" for l in gold["exact_lines"][:20]],
        "conversation_arc:", f"  start: {arc['start']}",
        f"  actual_problem: {arc['actual_problem']}",
        f"  optimization_target: {arc['optimization_target']}",
    ])

def write_outputs(context_path: Path, out: Path | None, out_dir: Path | None) -> list[Path]:
    text = normalize(read_text(context_path))
    arc = reconstruct_arc(text)
    candidates = identify_candidate_skills(text)
    packaging = choose_packaging(candidates)
    gold = preserve_gold(text)
    outputs: list[Path] = []
    chosen = [candidates[0]["name"]] if packaging == "single_best_skill" else [c["name"] for c in candidates[:3]]
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(emit_skill(chosen[0], arc, gold), encoding="utf-8")
        outputs.append(out)
        return outputs
    target_dir = out_dir or Path("skills")
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in chosen:
        path = target_dir / f"{name}.md"
        path.write_text(emit_skill(name, arc, gold), encoding="utf-8")
        outputs.append(path)
    return outputs

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract skill.md files from a conversation transcript.")
    parser.add_argument("--context", required=True, help="Path to conversation transcript")
    parser.add_argument("--out", default=None, help="Write a single skill file to this path")
    parser.add_argument("--out-dir", default=None, help="Directory for emitted skill files")
    args = parser.parse_args()
    context_path = Path(args.context)
    if not context_path.exists():
        print(f"Error: context file not found: {context_path}", file=sys.stderr)
        sys.exit(1)
    written = write_outputs(
        context_path,
        Path(args.out) if args.out else None,
        Path(args.out_dir) if args.out_dir else None,
    )
    for path in written:
        print(path)

if __name__ == "__main__":
    main()
