from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

# Remove the legacy combined Utilities & Boiler option from HR department choices.
old_options = '''                dept_options = sorted(set(dept_options) | {
                    "Boiler",
                    "Utility - VB (Vendor Boy)",
                })
'''
new_options = '''                legacy_combined_departments = {
                    "utilities & boiler", "utility & boiler", "utility boiler", "utilities boiler"
                }
                dept_options = sorted(
                    {
                        d for d in set(dept_options)
                        if " ".join(
                            _clean_text(d).lower().replace("_", " ").replace("-", " ").split()
                        ) not in legacy_combined_departments
                    }
                    | {"Boiler", "Utility - VB (Vendor Boy)"}
                )
'''
if old_options not in text:
    raise SystemExit('Current Boiler/Utility VB options block not found')
text = text.replace(old_options, new_options, 1)

old_save = '''                                elif dept_key == "boiler":
                                    department = "Boiler"
'''
new_save = '''                                elif dept_key in {
                                    "boiler", "utilities & boiler", "utility & boiler",
                                    "utility boiler", "utilities boiler"
                                }:
                                    department = "Boiler"
'''
if old_save not in text:
    raise SystemExit('Current Boiler canonicalization block not found')
text = text.replace(old_save, new_save, 1)

p.write_text(text, encoding='utf-8')
