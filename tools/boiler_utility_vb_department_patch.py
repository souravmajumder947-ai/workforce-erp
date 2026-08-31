from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

# Keep Boiler and Utility VB as separate canonical HR departments.
options_anchor = '''                except Exception:\n                    dept_options = []\n\n                m1,m2,m3,m4 = st.columns([1,1.25,1.15,1.0])\n'''
options_replacement = '''                except Exception:\n                    dept_options = []\n\n                # Boiler and Utility VB are separate work areas.\n                # VB means Vendor Boy and must never be treated as Boiler.\n                dept_options = sorted(set(dept_options) | {\n                    "Boiler",\n                    "Utility - VB (Vendor Boy)",\n                })\n                st.caption(\n                    "Department rule: **Boiler** and **Utility - VB (Vendor Boy)** are separate. "\n                    "VB means Vendor Boy and is never mapped to Boiler."\n                )\n\n                m1,m2,m3,m4 = st.columns([1,1.25,1.15,1.0])\n'''
if options_anchor not in text:
    raise SystemExit('Department options anchor not found')
text = text.replace(options_anchor, options_replacement, 1)

save_anchor = '''                                if bulk_master_shift != "Keep Each Row Shift":\n                                    shift = bulk_master_shift\n                                cur.execute(\n'''
save_replacement = '''                                if bulk_master_shift != "Keep Each Row Shift":\n                                    shift = bulk_master_shift\n\n                                # Canonicalize only the Utility-VB aliases. Boiler remains separate.\n                                dept_key = " ".join(\n                                    department.lower().replace("_", " ").replace("-", " ").split()\n                                )\n                                if dept_key in {\n                                    "utility vb", "utility vendor boy", "vendor boy", "vb"\n                                }:\n                                    department = "Utility - VB (Vendor Boy)"\n                                elif dept_key == "boiler":\n                                    department = "Boiler"\n\n                                cur.execute(\n'''
if save_anchor not in text:
    raise SystemExit('Employee master save anchor not found')
text = text.replace(save_anchor, save_replacement, 1)

p.write_text(text, encoding='utf-8')
