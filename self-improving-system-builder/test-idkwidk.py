#!/usr/bin/env python3
import sys
from pathlib import Path
def check(project_dir):
    project = Path(project_dir)
    results = []
    results.append(("IDKWIDK.md present", (project / "IDKWIDK.md").exists()))
    results.append(("session-open.sh present", (project / "session-open.sh").exists()))
    results.append(("RESUME.md present", (project / "RESUME.md").exists()))
    print(f"\nIDKWIDK Protocol Check: {project}")
    print("=" * 50)
    all_pass = True
    for name, passed in results:
        status = "+" if passed else "-"
        if not passed:
            all_pass = False
        print(f"  {status} {name}")
    print("=" * 50)
    print(f"Result: {'ALL CHECKS PASS' if all_pass else 'SOME CHECKS FAILED'}")
    return all_pass
if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    check(target)
