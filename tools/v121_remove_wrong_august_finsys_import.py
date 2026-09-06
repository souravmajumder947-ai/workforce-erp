from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")

MARK="# V12.1 REMOVE WRONG AUGUST FINSYS IMPORT"
if MARK in s:
    print("V12.1 wrong August import cleanup already applied")
    raise SystemExit(0)

# Make the old importer permanently inactive so the incorrect report can never repopulate.
old='''def ensure_finsys_aug2026_corrugation_daily_import():
    """Idempotently load August 2026 Finsys daily Corrugation totals into live production."""
'''
new='''def ensure_finsys_aug2026_corrugation_daily_import():
    """Deprecated: the previously supplied August 2026 Finsys DPR was confirmed incorrect."""
    # V12.1 REMOVE WRONG AUGUST FINSYS IMPORT
    return {"inserted":0,"updated":0,"preserved":0,"source_rows":0,"disabled":True}

def _v121_remove_wrong_august_finsys_rows():
    """Remove only rows created from the incorrect Finsys DPR import; preserve manual/live entries."""
    conn=get_pg_conn()
    try:
        cur=conn.cursor()
        cur.execute(
            """DELETE FROM production
               WHERE work_date BETWEEN %s AND %s
                 AND shift='DAY'
                 AND machine='Corrugation'
                 AND COALESCE(remark,'') LIKE 'FINSYS DPR IMPORT%%'""",
            ("2026-08-01","2026-08-31")
        )
        deleted=int(cur.rowcount or 0)
        cur.execute(
            "DELETE FROM app_settings WHERE setting_key=%s",
            ("finsys_corrugation_aug2026_import_v1",)
        )
        conn.commit()
        cur.close()
        return deleted
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

try:
    _v121_removed_wrong_rows=_v121_remove_wrong_august_finsys_rows()
except Exception:
    _v121_removed_wrong_rows=0

def _v121_old_importer_disabled():
'''
if old not in s:
    raise RuntimeError("Old Finsys importer anchor not found")
s=s.replace(old,new,1)

# Remove the remainder of the old importer body by replacing from our inserted dummy marker
# up to the next function definition we know follows it.
start=s.find('def _v121_old_importer_disabled():')
end=s.find('\n\ndef can_view_salary(role):', start)
if start==-1 or end==-1:
    raise RuntimeError("Unable to isolate old importer body")
s=s[:start] + '''def _v121_old_importer_disabled():
    return True
''' + s[end:]

# Remove old boot auto-load block if present.
boot='''# Auto-load the approved August 2026 production history once after deployment.
# Failure is non-fatal; Operations page retries and shows the error if needed.
try:
    _v119_boot_import = ensure_finsys_aug2026_corrugation_daily_import()
except Exception:
    _v119_boot_import = None


'''
s=s.replace(boot,'',1)

# Replace Operations auto-import call with a clear correction notice.
old_ops='''    # Load the approved historical August 2026 DPR into the live production table.
    try:
        _v119_import_result = ensure_finsys_aug2026_corrugation_daily_import()
    except Exception as _v119_import_exc:
        _v119_import_result = None
        st.error(f"August 2026 production history import failed: {_v119_import_exc}")

'''
new_ops='''    # V12.1: incorrect August Finsys DPR import was removed.
    _v119_import_result = None
'''
if old_ops in s:
    s=s.replace(old_ops,new_ops,1)

old_caption='''    if _v119_import_result:
        st.caption(
            "August 2026 Finsys DPR history is loaded day-wise for Corrugation: "
            f"{_v119_import_result['source_rows']} production date(s) in source; "
            "02 Aug and 15 Aug had no DPR date record and were not invented."
        )

'''
new_caption='''    st.caption(
        "The previously imported August 2026 Finsys production report was removed because the source report was confirmed incorrect. "
        "Manual/live production entries are preserved."
    )

'''
if old_caption in s:
    s=s.replace(old_caption,new_caption,1)

p.write_text(s,encoding="utf-8")
print("Applied V12.1 cleanup of incorrect August Finsys production import")
