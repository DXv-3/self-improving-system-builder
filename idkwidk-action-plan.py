#!/usr/bin/env python3
"""IDKWIDK Action Plan Generator - converts audit findings into tracked actions."""
import json, os, sys
from pathlib import Path
from datetime import datetime
STORE = Path(os.getenv("IDKWIDK_STORE", str(Path.home() / ".idkwidk")))
ACTION_FILE = STORE / "action-plan.json"
GATE_PRIORITY = {"Gate 3": "critical", "Gate 2": "high", "Gate 4": "high", "Gate 7": "critical", "Gate 5": "medium", "Gate 1": "low", "Gate 6": "low"}
GATE_VERBS = {"Gate 2": "Build", "Gate 3": "Fix", "Gate 4": "Investigate", "Gate 5": "Document", "Gate 6": "Simplify", "Gate 1": "Address", "Gate 7": "DO NOW"}
STATUS_ICONS = {"open": "[ ]", "in-progress": "[~]", "done": "[x]", "blocked": "[!]", "deferred": "[-]", "wontfix": "[/]"}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "nice-to-have": 4}
STATUS_ORDER = {"open": 0, "in-progress": 1, "blocked": 2, "deferred": 3, "done": 4, "wontfix": 5}
def init_store():
    STORE.mkdir(parents=True, exist_ok=True)
    if not ACTION_FILE.exists():
        ACTION_FILE.write_text(json.dumps({"actions": [], "created": datetime.utcnow().isoformat() + "Z", "last_updated": datetime.utcnow().isoformat() + "Z"}, indent=2))
def load_plan():
    init_store()
    return json.loads(ACTION_FILE.read_text())
def save_plan(plan):
    plan["last_updated"] = datetime.utcnow().isoformat() + "Z"
    ACTION_FILE.write_text(json.dumps(plan, indent=2))
def parse_audit(audit_json):
    plan = load_plan()
    existing = {a["description"] for a in plan["actions"]}
    new_actions = []
    gates = audit_json.get("gates", audit_json)
    gate7_items = []
    for gate_name, findings in gates.items():
        if not findings or findings == "PASS":
            continue
        if "Gate 7" in gate_name or "Do This Next" in str(gate_name):
            gate7_items = findings if isinstance(findings, list) else [findings]
            continue
        gate_key = next((k for k in GATE_PRIORITY if k in str(gate_name)), "Gate 1")
        priority = GATE_PRIORITY[gate_key]
        verb = GATE_VERBS.get(gate_key, "Address")
        if isinstance(findings, str):
            findings = [findings]
        elif isinstance(findings, dict):
            findings = list(findings.values()) if findings else []
        for finding in findings:
            desc = str(finding)[:500]
            if desc in existing:
                continue
            effort = "30 min" if priority in ("critical", "high") else "1 hour"
            new_actions.append({"id": len(plan["actions"]) + len(new_actions) + 1, "gate": gate_name, "priority": priority, "action": verb + ": " + desc[:100], "description": desc, "status": "open", "created": datetime.utcnow().isoformat() + "Z", "completed": None, "blocker": None, "effort_estimate": effort})
    for i, item in enumerate(gate7_items):
        desc = str(item)[:500]
        if desc in existing:
            continue
        new_actions.append({"id": len(plan["actions"]) + len(new_actions) + 1, "gate": "Gate 7: Do This Next", "priority": "critical", "action": "DO NOW (" + str(i + 1) + "): " + desc[:100], "description": desc, "status": "open", "created": datetime.utcnow().isoformat() + "Z", "completed": None, "blocker": None, "effort_estimate": "30 min"})
    plan["actions"].extend(new_actions)
    save_plan(plan)
    return new_actions
def show_status():
    plan = load_plan()
    actions = plan["actions"]
    if not actions:
        print("No actions in plan. Run an IDKWIDK audit first.")
        return
    sorted_actions = sorted(actions, key=lambda a: (PRIORITY_ORDER.get(a.get("priority", "medium"), 2), STATUS_ORDER.get(a.get("status", "open"), 0), a.get("id", 999)))
    print("=" * 80)
    print("IDKWIDK ACTION PLAN")
    print("=" * 80)
    done_c = sum(1 for a in actions if a.get("status") == "done")
    rate = (done_c / len(actions) * 100) if actions else 0
    print(f"  Completion: {int(rate)}% ({done_c}/{len(actions)})")
    current = None
    for a in sorted_actions:
        p = a.get("priority", "medium")
        if p != current:
            current = p
            print(f"\n--- {p.upper()} ---")
        icon = STATUS_ICONS.get(a.get("status", "open"), "[ ]")
        text = a.get("action", a.get("description", "?"))[:80]
        print(f"  {icon} #{str(a.get('id','?')):<3} {text}")
def mark_status(action_id, new_status, reason=None):
    plan = load_plan()
    for a in plan["actions"]:
        if a.get("id") == action_id:
            a["status"] = new_status
            if new_status == "done":
                a["completed"] = datetime.utcnow().isoformat() + "Z"
            if reason:
                a["blocker"] = reason
            save_plan(plan)
            print(f"Marked #{action_id} as {new_status.upper()}: {a.get('action','')[:60]}")
            return
    print(f"Action #{action_id} not found.")
def main():
    if len(sys.argv) < 2:
        show_status()
        return
    arg = sys.argv[1]
    if arg in ("--status", "-s"): show_status()
    elif arg in ("--done", "-d"):
        if len(sys.argv) < 3: print("Usage: --done <id>"); return
        mark_status(int(sys.argv[2]), "done")
    elif arg in ("--block", "-b"):
        if len(sys.argv) < 4: print("Usage: --block <id> <reason>"); return
        mark_status(int(sys.argv[2]), "blocked", " ".join(sys.argv[3:]))
    elif arg in ("--start", "-i"):
        if len(sys.argv) < 3: print("Usage: --start <id>"); return
        mark_status(int(sys.argv[2]), "in-progress")
    elif arg in ("--defer", "-f"):
        if len(sys.argv) < 3: print("Usage: --defer <id>"); return
        mark_status(int(sys.argv[2]), "deferred")
    elif arg == "--json": print(json.dumps(load_plan(), indent=2))
    elif arg == "--reset":
        init_store()
        save_plan({"actions": [], "created": datetime.utcnow().isoformat() + "Z", "last_updated": datetime.utcnow().isoformat() + "Z"})
        print("Action plan reset.")
    else:
        audit = json.loads(sys.stdin.read()) if arg == "-" else json.loads(Path(arg).read_text())
        new_actions = parse_audit(audit)
        print(f"Generated {len(new_actions)} new actions from audit.")
        show_status()
if __name__ == "__main__":
    main()
