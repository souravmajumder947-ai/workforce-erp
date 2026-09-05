from pathlib import Path
import re
import sys

s = Path("app.py").read_text(encoding="utf-8")
lines = s.splitlines()

# 1) Every ordinary .button() call must be consumed by an if-condition or assignment.
button_issues = []
for i, line in enumerate(lines, 1):
    if ".button(" not in line:
        continue
    stripped = line.strip()
    if stripped.startswith("if ") or re.search(r"=\s*.*\.button\s*\(", stripped):
        continue
    button_issues.append((i, stripped))

# 2) Literal widget keys should not be duplicated.
keys = re.findall(r'key\s*=\s*"([^"]+)"', s)
dups = sorted({k for k in keys if keys.count(k) > 1})

# 3) Navigation requests must target actual modules.
allowed = {
    "Home","Management","Employees","Attendance","Payroll","Contractors",
    "Operations","Reports","AI Tools","Master Centre","User Management"
}
targets = re.findall(r'_v83_nav_request"\]\s*=\s*"([^"]+)"', s)
bad_targets = sorted(set(targets) - allowed)

if button_issues or dups or bad_targets:
    if button_issues:
        print("Unconsumed button calls:", button_issues)
    if dups:
        print("Duplicate literal widget keys:", dups)
    if bad_targets:
        print("Invalid nav targets:", bad_targets)
    sys.exit(1)

print(f"UI control audit passed: {len(keys)} literal keys, {len(set(targets))} nav targets, no orphan button calls.")
