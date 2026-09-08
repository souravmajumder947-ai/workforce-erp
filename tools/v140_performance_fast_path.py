from pathlib import Path

p=Path("app.py")
s=p.read_text(encoding="utf-8")
MARK="# V14.0 PERFORMANCE FAST PATH"
if MARK in s:
    print("V14.0 already applied")
    raise SystemExit(0)

# ------------------------------------------------------------
# 1) Fast read path: one DB round-trip per SELECT.
#    Retry stale Neon connections only when the real query fails.
# ------------------------------------------------------------
start=s.find("def read_df(sql, params=()):")
end=s.find("\n\ndef upsert(sql, params):",start)
if start==-1 or end==-1:
    raise RuntimeError("read_df block not found")

new_read='''def read_df(sql, params=()):
    """Fast read-only PostgreSQL path using pooled autocommit connections."""
    pg_sql = sql.replace("?", "%s")
    pool = _postgres_pool()
    last_error = None

    for _attempt in range(3):
        raw = None
        returned = False
        try:
            raw = pool.getconn()
            if raw is None or raw.closed:
                _discard_raw_pg_connection(pool, raw)
                raw = None
                continue

            # Read queries do not need a transaction. This avoids an extra
            # ROLLBACK round-trip for every SELECT.
            raw.autocommit = True
            cur = raw.cursor()
            try:
                cur.execute(pg_sql, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
            finally:
                cur.close()

            result = _normalize_postgres_numbers(pd.DataFrame(rows, columns=columns))

            try:
                raw.autocommit = False
            except Exception:
                pass
            pool.putconn(raw)
            returned = True
            raw = None
            return result

        except _PG_TRANSIENT_ERRORS as exc:
            last_error = exc
            if raw is not None:
                _discard_raw_pg_connection(pool, raw)
                raw = None
            if _attempt >= 2:
                raise
            continue
        except Exception:
            if raw is not None:
                try:
                    raw.autocommit = False
                except Exception:
                    pass
                try:
                    pool.putconn(raw)
                    returned = True
                except Exception:
                    _discard_raw_pg_connection(pool, raw)
                raw = None
            raise
        finally:
            if raw is not None and not returned:
                try:
                    raw.autocommit = False
                except Exception:
                    pass
                try:
                    pool.putconn(raw)
                except Exception:
                    _discard_raw_pg_connection(pool, raw)

    if last_error is not None:
        raise last_error
    return pd.DataFrame()
'''
s=s[:start]+new_read+s[end:]

# ------------------------------------------------------------
# 2) Stop pinging PostgreSQL before every write checkout.
#    Existing write retry/discard logic already handles stale connections.
# ------------------------------------------------------------
start=s.find("def get_pg_conn():")
end=s.find("\n\ndef test_postgres_connection():",start)
if start==-1 or end==-1:
    raise RuntimeError("get_pg_conn block not found")

new_conn='''def get_pg_conn():
    """Return a pooled PostgreSQL connection without a redundant preflight query."""
    pool = _postgres_pool()
    last_error = None

    for _attempt in range(3):
        conn = None
        try:
            conn = pool.getconn()
            if conn is None or conn.closed:
                _discard_raw_pg_connection(pool, conn)
                continue
            return _PooledConnection(pool, conn)
        except _PG_TRANSIENT_ERRORS as exc:
            last_error = exc
            _discard_raw_pg_connection(pool, conn)
            continue
        except Exception:
            _discard_raw_pg_connection(pool, conn)
            raise

    if last_error is not None:
        raise last_error
    raise RuntimeError("Unable to obtain a PostgreSQL connection.")
'''
s=s[:start]+new_conn+s[end:]

# ------------------------------------------------------------
# 3) Sidebar alerts / heartbeat: cache short-lived status reads.
# ------------------------------------------------------------
old='''def _v94_scalar(sql, params=()):
'''
new='''@st.cache_data(ttl=30, show_spinner=False)
def _v94_scalar(sql, params=()):
'''
if old not in s:
    raise RuntimeError("_v94_scalar anchor not found")
s=s.replace(old,new,1)

old='''def _v83_system_online():
'''
new='''@st.cache_data(ttl=60, show_spinner=False)
def _v83_system_online():
'''
if old not in s:
    raise RuntimeError("_v83_system_online anchor not found")
s=s.replace(old,new,1)

# ------------------------------------------------------------
# 4) Remove obsolete August cleanup write from every app rerun.
# ------------------------------------------------------------
old='''try:
    _v121_removed_wrong_rows=_v121_remove_wrong_august_finsys_rows()
except Exception:
    _v121_removed_wrong_rows=0
'''
new='''# V14.0 PERFORMANCE FAST PATH
# The incorrect historical import was already removed. Do not issue DELETEs on every rerun.
_v121_removed_wrong_rows=0
'''
if old not in s:
    raise RuntimeError("Repeated V12.1 cleanup call not found")
s=s.replace(old,new,1)

# ------------------------------------------------------------
# 5) Prepare production/reel schema once per Streamlit process,
#    and add report indexes.
# ------------------------------------------------------------
ops_anchor='''# ============================================================
# OPERATIONS — GROUPED, NOT THREE SIDEBAR PAGES
# ============================================================
'''
if ops_anchor not in s:
    raise RuntimeError("Operations anchor not found")

helper='''@st.cache_resource(show_spinner=False)
def _v140_prepare_production_runtime_schema():
    """One-time production/reel schema check and report indexes."""
    conn=get_pg_conn()
    try:
        cur=conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS production_reel_consumption(
                id BIGSERIAL PRIMARY KEY,
                work_date DATE NOT NULL,
                machine TEXT NOT NULL,
                line_no INTEGER NOT NULL,
                reel_reference TEXT,
                paper_grade TEXT,
                quantity_ton NUMERIC(14,4) NOT NULL DEFAULT 0,
                value_amount NUMERIC(16,2) NOT NULL DEFAULT 0,
                remark TEXT,
                entered_by TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(work_date,machine,line_no)
            )
            """
        )
        for stmt in [
            "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS opening_wip_ton NUMERIC(14,4) NOT NULL DEFAULT 0",
            "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS reel_issue_ton NUMERIC(14,4) NOT NULL DEFAULT 0",
            "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS reel_return_ton NUMERIC(14,4) NOT NULL DEFAULT 0",
            "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS net_issue_ton NUMERIC(14,4) NOT NULL DEFAULT 0",
            "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS closing_wip_ton NUMERIC(14,4) NOT NULL DEFAULT 0",
            "ALTER TABLE production_reel_consumption ADD COLUMN IF NOT EXISTS consumption_ton NUMERIC(14,4) NOT NULL DEFAULT 0",
        ]:
            cur.execute(stmt)

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS production_reel_transactions(
                id BIGSERIAL PRIMARY KEY,
                movement_type TEXT NOT NULL,
                work_date DATE NOT NULL,
                vch_no TEXT,
                supplier TEXT,
                acode TEXT,
                item TEXT,
                quantity_kg NUMERIC(14,3) NOT NULL DEFAULT 0,
                quantity_ton NUMERIC(14,6) NOT NULL DEFAULT 0,
                reel_no TEXT,
                co_reel TEXT,
                reel_mill TEXT,
                irate NUMERIC(14,4) NOT NULL DEFAULT 0,
                movement_value NUMERIC(16,2) NOT NULL DEFAULT 0,
                job_no TEXT,
                job_date DATE,
                reel_size NUMERIC(14,3) NOT NULL DEFAULT 0,
                gsm NUMERIC(14,3) NOT NULL DEFAULT 0,
                icode TEXT,
                cpartno TEXT,
                source_file TEXT,
                source_row INTEGER,
                entered_by TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(movement_type,work_date,source_file,source_row)
            )
            """
        )
        cur.execute(
            """UPDATE production_reel_consumption
               SET consumption_ton=quantity_ton
               WHERE COALESCE(consumption_ton,0)=0
                 AND COALESCE(quantity_ton,0)>0"""
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_prc_date_machine ON production_reel_consumption(work_date,machine)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_prt_type_date ON production_reel_transactions(movement_type,work_date)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_prt_date_reel ON production_reel_transactions(work_date,reel_no)"
        )
        conn.commit()
        cur.close()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


'''
s=s.replace(ops_anchor,helper+ops_anchor,1)

# Replace expensive inline DDL/migration executed on every Operations rerun.
ddl_start=s.find('''        # Reel-consumption detail is stored separately and rolls up into the daily Corrugation record.
        try:
            _v118_conn = get_pg_conn()
''')
ddl_end=s.find('''        c1,c2=st.columns([1,1.4])
''',ddl_start)
if ddl_start==-1 or ddl_end==-1:
    raise RuntimeError("Inline production schema block not found")

fast_schema='''        # Schema/index preparation is cached once per Streamlit process.
        try:
            _v140_prepare_production_runtime_schema()
        except Exception as _v140_schema_exc:
            st.error(f"Unable to prepare production storage: {_v140_schema_exc}")
            st.stop()

'''
s=s[:ddl_start]+fast_schema+s[ddl_end:]

# ------------------------------------------------------------
# 6) Streamlit tabs execute ALL tab bodies. Replace heavy tabs
#    with one-section-at-a-time radio navigation.
# ------------------------------------------------------------

# Employee 360 profile.
old='''                profile_tabs=st.tabs([
                    "Overview","Attendance","Payroll","Work History","Statutory & Bank","Timeline"
                ])
'''
new='''                _v140_profile_section=st.radio(
                    "Employee View",
                    ["Overview","Attendance","Payroll","Work History","Statutory & Bank","Timeline"],
                    horizontal=True,
                    key=f"v140_employee_profile_{emp_id}"
                )
'''
if old in s:
    s=s.replace(old,new,1)
    for idx,name in enumerate(["Overview","Attendance","Payroll","Work History","Statutory & Bank","Timeline"]):
        s=s.replace(f"                with profile_tabs[{idx}]:",f'                if _v140_profile_section=="{name}":',1)

# Attendance.
old='''    tab_upload, tab_daily, tab_review, tab_month = st.tabs(
        ["Upload Attendance","Daily Register","HR Review","Monthly Summary"]
    )
'''
new='''    _v140_att_section=st.radio(
        "Attendance View",
        ["Upload Attendance","Daily Register","HR Review","Monthly Summary"],
        horizontal=True,
        key="v140_attendance_section"
    )
'''
if old not in s:
    raise RuntimeError("Attendance tabs anchor not found")
s=s.replace(old,new,1)
for var,name in [
    ("tab_upload","Upload Attendance"),
    ("tab_daily","Daily Register"),
    ("tab_review","HR Review"),
    ("tab_month","Monthly Summary"),
]:
    s=s.replace(f"    with {var}:",f'    if _v140_att_section=="{name}":',1)

# Payroll.
old='''        tab_live,tab_adj,tab_final=st.tabs(["Live Payroll","Adjustments","Finalize & History"])
'''
new='''        _v140_pay_section=st.radio(
            "Payroll View",
            ["Live Payroll","Adjustments","Finalize & History"],
            horizontal=True,
            key="v140_payroll_section"
        )
'''
if old not in s:
    raise RuntimeError("Payroll tabs anchor not found")
s=s.replace(old,new,1)
for var,name in [
    ("tab_live","Live Payroll"),
    ("tab_adj","Adjustments"),
    ("tab_final","Finalize & History"),
]:
    s=s.replace(f"        with {var}:",f'        if _v140_pay_section=="{name}":',1)

# Contractors.
old='''    tab_overview,tab_work=st.tabs(["Overview","Work Entry"])
'''
new='''    _v140_con_section=st.radio(
        "Contractor View",
        ["Overview","Work Entry"],
        horizontal=True,
        key="v140_contractor_section"
    )
'''
if old not in s:
    raise RuntimeError("Contractor tabs anchor not found")
s=s.replace(old,new,1)
s=s.replace("    with tab_overview:",'    if _v140_con_section=="Overview":',1)
s=s.replace("    with tab_work:",'    if _v140_con_section=="Work Entry":',1)

# Operations — very important: Production Entry no longer runs while viewing reports.
old='''    tab_prod,tab_report_centre,tab_mp=st.tabs([
        "Production Entry","Report Centre","Manpower Allocation"
    ])
'''
new='''    _v140_ops_section=st.radio(
        "Operations View",
        ["Production Entry","Report Centre","Manpower Allocation"],
        horizontal=True,
        key="v140_operations_section"
    )
'''
if old not in s:
    raise RuntimeError("Operations tabs anchor not found")
s=s.replace(old,new,1)
s=s.replace("    with tab_prod:",'    if _v140_ops_section=="Production Entry":',1)
s=s.replace("    with tab_report_centre:",'    if _v140_ops_section=="Report Centre":',1)
s=s.replace("    with tab_mp:",'    if _v140_ops_section=="Manpower Allocation":',1)

# AI Tools.
old='''    tab1,tab2,tab3,tab4,tab5 = st.tabs(
        ["Workforce Visualizer","Attendance Intelligence","Payroll Risk","Ask HR Data","Automation Hub"]
    )
'''
new='''    _v140_ai_section=st.radio(
        "AI Tools View",
        ["Workforce Visualizer","Attendance Intelligence","Payroll Risk","Ask HR Data","Automation Hub"],
        horizontal=True,
        key="v140_ai_section"
    )
'''
if old not in s:
    raise RuntimeError("AI Tools tabs anchor not found")
s=s.replace(old,new,1)
for idx,name in enumerate([
    "Workforce Visualizer","Attendance Intelligence","Payroll Risk","Ask HR Data","Automation Hub"
],start=1):
    s=s.replace(f"    with tab{idx}:",f'    if _v140_ai_section=="{name}":',1)

# Marker at end for idempotence.
s += "\n# V14.0 PERFORMANCE FAST PATH\n"
p.write_text(s,encoding="utf-8")
print("Applied V14.0 performance fast path")
