from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

old_options = '''                    ["Keep Each Row Status","Present","Half Day","Absent","LWP","WO","Holiday","Leave","CL","SL","EL","HR Review"],
                    key="v80_bulk_review_status"
'''
new_options = '''                    ["Keep Each Row Status","Use Raw Biometric Status (Auto)","Present","Half Day","Absent","LWP","WO","Holiday","Leave","CL","SL","EL","HR Review"],
                    key="v82_bulk_review_status"
'''
if old_options not in text:
    raise SystemExit('Bulk status options target not found; patch stopped safely.')
text = text.replace(old_options, new_options, 1)

old_logic = '''                                final_status = str(r["Status"])
                                if bulk_status != "Keep Each Row Status":
                                    final_status = bulk_status
'''
new_logic = '''                                final_status = str(r["Status"])
                                if bulk_status == "Use Raw Biometric Status (Auto)":
                                    final_status = _map_attendance_status(
                                        r["Raw Status"], r["Working Hrs"], r["Time In"], r["Time Out"]
                                    )
                                elif bulk_status != "Keep Each Row Status":
                                    final_status = bulk_status
'''
if old_logic not in text:
    raise SystemExit('Resolve status logic target not found; patch stopped safely.')
text = text.replace(old_logic, new_logic, 1)

old_caption = '''                    f"Selected: {selected_count:,} row(s). Bulk Status/Division, when chosen, is applied only to selected rows. "
                    "Raw Status is read-only and kept for biometric audit."
'''
new_caption = '''                    f"Selected: {selected_count:,} row(s). For division mismatch, choose 'Use Raw Biometric Status (Auto)' "
                    "to convert PP→Present, WO→WO, AA→Absent, EL→EL while keeping incomplete punches in HR Review. "
                    "Raw Status remains read-only for biometric audit."
'''
if old_caption in text:
    text = text.replace(old_caption, new_caption, 1)

p.write_text(text, encoding='utf-8')
