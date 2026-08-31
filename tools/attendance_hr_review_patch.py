from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

marker = '# FK-HR-REVIEW-PLACEHOLDER-V1'
if marker in text:
    print('Attendance FK placeholder patch already applied')
    raise SystemExit(0)

old = '''def _bulk_upsert_attendance(records, source_type):
    if not records:
        return 0
    records = _validate_and_enrich_attendance_records(records)
    conn = get_pg_conn()
'''

new = '''def _bulk_upsert_attendance(records, source_type):
    if not records:
        return 0
    records = _validate_and_enrich_attendance_records(records)

    # FK-HR-REVIEW-PLACEHOLDER-V1
    # attendance.employee_id references employees.employee_id. Unknown biometric
    # employees therefore need a temporary master reference before their rows can
    # be stored for HR Review. Existing master records are never overwritten here.
    unknown_records = [
        rec for rec in records
        if _clean_text(rec.get("source_issue")) == "Employee ID not found in Employee Master"
    ]
    if unknown_records:
        conn_master = get_pg_conn()
        try:
            cur_master = conn_master.cursor()
            for rec in unknown_records:
                emp_id = str(rec.get("employee_id", "")).strip()
                if not emp_id:
                    continue
                emp_name = _clean_text(rec.get("source_employee_name")) or _clean_text(rec.get("employee_name")) or emp_id
                designation = _clean_text(rec.get("designation")) or "Employee"
                division = _clean_text(rec.get("division")) or "Greater Noida Plant"
                shift = _clean_text(rec.get("shift"))
                if shift not in ("A", "B"):
                    shift = "General"
                cur_master.execute(
                    """INSERT INTO employees(
                           employee_id,employee_name,department,designation,
                           employee_type,shift,division,status
                       ) VALUES (%s,%s,'HR Review',%s,'Permanent',%s,%s,'Active')
                       ON CONFLICT(employee_id) DO NOTHING""",
                    (emp_id, emp_name, designation, shift, division)
                )
            conn_master.commit()
            cur_master.close()
        except Exception:
            conn_master.rollback()
            raise
        finally:
            conn_master.close()

    conn = get_pg_conn()
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f'bulk attendance target expected once, found {count}')

text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
print('Attendance FK placeholder patch applied')
