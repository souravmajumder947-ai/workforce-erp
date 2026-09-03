from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

replacements = {
    'datetime.now(IST).strftime("%d %b %Y · %I:%M:%S %p")': 'datetime.now(IST).strftime("%d %b %Y · %H:%M:%S")',
    'parsed.dt.strftime("%d %b %Y · %I:%M %p").fillna(empty_text)': 'parsed.dt.strftime("%d %b %Y · %H:%M").fillna(empty_text)',
}

for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f'24-hour time anchor not found: {old}')
    text = text.replace(old, new)

# Keep AM/PM parsing for legacy/source compatibility, but all user-facing output is 24-hour.
# The browser live clock already uses Intl with hour12:false.

p.write_text(text, encoding='utf-8')
