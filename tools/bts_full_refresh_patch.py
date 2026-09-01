from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

old = '"DELETE FROM attendance WHERE division=%s AND work_date = ANY(%s)",'
new = '"DELETE FROM attendance WHERE division=%s AND work_date = ANY(%s::date[])",'
if old not in text:
    raise SystemExit('BTS full refresh delete query anchor not found')
text = text.replace(old, new, 1)
p.write_text(text, encoding='utf-8')
