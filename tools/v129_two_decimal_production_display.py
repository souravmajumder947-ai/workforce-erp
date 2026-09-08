from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V12.9 TWO DECIMAL PRODUCTION DISPLAY"
if MARK in s:
    print("V12.9 already applied")
    raise SystemExit(0)

# Keep database precision unchanged; only simplify what users see.
s += "\n# V12.9 TWO DECIMAL PRODUCTION DISPLAY\n"

repls = [
    ('format="%.3f T"', 'format="%.2f T"'),
    ("format='%.3f T'", "format='%.2f T'"),
    (':,.3f} T"', ':,.2f} T"'),
    (':.3f} T"', ':.2f} T"'),
    (":,.3f} T'", ":,.2f} T'"),
    (":.3f} T'", ":.2f} T'"),
]

changed=0
for a,b in repls:
    n=s.count(a)
    if n:
        s=s.replace(a,b)
        changed+=n

p.write_text(s,encoding="utf-8")
print(f"Applied V12.9 two-decimal production display; replacements={changed}")
