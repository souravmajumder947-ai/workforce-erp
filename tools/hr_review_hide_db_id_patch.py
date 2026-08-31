from pathlib import Path

p = Path("app.py")
text = p.read_text(encoding="utf-8")

old = '''                    column_config={
                        "Select":st.column_config.CheckboxColumn("Select",default=False),
                        "Division":st.column_config.SelectboxColumn("Division",options=DIVISIONS,required=True),
'''
new = '''                    column_config={
                        "ID": None,
                        "Select":st.column_config.CheckboxColumn("Select",default=False),
                        "Division":st.column_config.SelectboxColumn("Division",options=DIVISIONS,required=True),
'''

if old not in text:
    raise SystemExit("HR Review editor target not found; patch stopped safely.")

text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
print("Internal attendance database ID hidden from HR Review table.")
