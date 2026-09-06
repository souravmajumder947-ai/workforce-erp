from pathlib import Path
p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V11.9B AUTO-LOAD FINSYS AUGUST HISTORY"
if MARK in s:
    print("already applied")
    raise SystemExit(0)

needle='''def ensure_finsys_aug2026_corrugation_daily_import():
    """Idempotently load August 2026 Finsys daily Corrugation totals into live production."""
    conn = get_pg_conn()
'''
replace='''def ensure_finsys_aug2026_corrugation_daily_import():
    """Idempotently load August 2026 Finsys daily Corrugation totals into live production."""
    # V11.9B AUTO-LOAD FINSYS AUGUST HISTORY
    try:
        _done = read_df(
            "SELECT setting_value FROM app_settings WHERE setting_key=? LIMIT 1",
            ("finsys_corrugation_aug2026_import_v1",)
        )
        if not _done.empty and str(_done.iloc[0].get("setting_value") or "").startswith("loaded:"):
            return {
                "inserted":0,"updated":0,"preserved":0,
                "source_rows":len(_FINSYS_AUG2026_CORRUGATION_DAILY),
                "already_loaded":True
            }
    except Exception:
        pass
    conn = get_pg_conn()
'''
if needle not in s:
    raise RuntimeError("helper start not found")
s=s.replace(needle,replace,1)

needle2='''def can_view_salary(role):
    return str(role) in {"Owner", "Admin", "HR", "Manager"}
'''
replace2='''# Auto-load the approved August 2026 production history once after deployment.
# Failure is non-fatal; Operations page retries and shows the error if needed.
try:
    _v119_boot_import = ensure_finsys_aug2026_corrugation_daily_import()
except Exception:
    _v119_boot_import = None


def can_view_salary(role):
    return str(role) in {"Owner", "Admin", "HR", "Manager"}
'''
if needle2 not in s:
    raise RuntimeError("can_view_salary anchor not found")
s=s.replace(needle2,replace2,1)

p.write_text(s,encoding="utf-8")
print("Applied V11.9B auto-load")
