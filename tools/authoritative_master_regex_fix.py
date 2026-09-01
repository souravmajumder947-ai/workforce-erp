from pathlib import Path
p=Path('app.py')
text=p.read_text(encoding='utf-8')
old="work = work[work['__employee_id'].astype(str).str.fullmatch(r'\\\\d+', na=False)].copy()"
new="work = work[work['__employee_id'].astype(str).str.fullmatch(r'\\d+', na=False)].copy()"
if old not in text:
    raise SystemExit('authoritative employee ID regex anchor not found')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
