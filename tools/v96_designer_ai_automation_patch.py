from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V9.6 DESIGNER AI AUTOMATION COMMAND CENTRE"
if MARK in s:
    print("V9.6 patch already applied")
    raise SystemExit(0)

def replace_once(old, new, label):
    global s
    if old not in s:
        raise RuntimeError(f"Anchor not found for {label}")
    s = s.replace(old, new, 1)

# Product/version presentation only.
replace_once(
    'page_title="Reliable Packaging HRMS V9.2 Real Wall Live Interface"',
    'page_title="Reliable Packaging HRMS V9.6 AI Command Centre"',
    "page title",
)
replace_once('<span>V8.3</span>', '<span>V9.6 AI</span>', "sidebar version")
replace_once(
    '<span class="v83-sync-pill">✦ <b>AI Tools</b> Ready</span>',
    '<span class="v83-sync-pill">✦ <b>AI Insights</b> Ready</span>',
    "live AI label",
)

# ---------------------------------------------------------------------
# HOME: AI operational command centre and automatic priority queue.
# This is deterministic, read-only decision support using the live HR DB.
# ---------------------------------------------------------------------
home_anchor = '''    v5_kpis([
        ("Active Employees", f"{active_count:,}", "Current live employee master", "blue"),'''
home_block = r'''    # V9.6 DESIGNER AI AUTOMATION COMMAND CENTRE
    # Local decision-support only: no company data is sent to an external AI service.
    _v96_penalty = min(
        28.0,
        (review * 0.45)
        + (attendance_pending * 0.16)
        + (payroll_exceptions * 0.22)
        + (_v94_master_pending * 0.40)
    )
    _v96_health = max(
        0.0,
        min(
            100.0,
            (attendance_rate * 0.50)
            + (salary_ready_pct * 0.25)
            + (dept_ready_pct * 0.25)
            - _v96_penalty,
        ),
    )
    if _v96_health >= 90:
        _v96_health_state, _v96_health_class = "EXCELLENT", "good"
    elif _v96_health >= 75:
        _v96_health_state, _v96_health_class = "STABLE", "blue"
    elif _v96_health >= 55:
        _v96_health_state, _v96_health_class = "ATTENTION", "warn"
    else:
        _v96_health_state, _v96_health_class = "ACTION REQUIRED", "danger"

    _v96_priorities = []
    if _v94_upload_pending:
        _v96_priorities.append(("HIGH", "Attendance source", f"Upload attendance for {global_work_date.strftime('%d %b %Y')}", "Attendance"))
    if _v94_review:
        _v96_priorities.append(("HIGH", "HR Review", f"{_v94_review:,} attendance exception(s) require review", "Attendance"))
    if _v94_missing:
        _v96_priorities.append(("MEDIUM", "Missing attendance", f"{_v94_missing:,} active employee(s) have no row on the selected date", "Attendance"))
    if salary_missing:
        _v96_priorities.append(("MEDIUM", "Salary master", f"{salary_missing:,} active employee(s) have no salary value", "Employees"))
    if dept_pending:
        _v96_priorities.append(("MEDIUM", "Department master", f"{dept_pending:,} employee mapping(s) need review", "Master Centre"))
    if payroll_exceptions:
        _v96_priorities.append(("HIGH", "Payroll blockers", f"{payroll_exceptions:,} employee(s) have HR-review payroll blockers", "Payroll"))
    if not _v96_priorities:
        _v96_priorities.append(("CLEAR", "Operations", "No priority exception detected in the selected context", "Home"))

    _v96_ai_message = (
        "Daily controls are healthy. Focus on trend monitoring and planned HR work."
        if _v96_health >= 90 else
        "Core HR data is stable, but the action queue should be cleared before payroll close."
        if _v96_health >= 75 else
        "The selected context has material HR exceptions. Resolve attendance and master gaps first."
        if _v96_health >= 55 else
        "Immediate operational cleanup is recommended before payroll or management close."
    )

    st.markdown(
        f"""
        <div class="v96-command-hero">
          <div class="v96-command-copy">
            <div class="v96-kicker">✦ RELIABLE AI COMMAND CENTRE</div>
            <div class="v96-command-title">Workforce health <span>{_v96_health_state}</span></div>
            <div class="v96-command-sub">{html.escape(_v96_ai_message)}</div>
            <div class="v96-chip-row">
              <span class="v96-chip">◉ Live DB</span>
              <span class="v96-chip">⚡ Auto-priority</span>
              <span class="v96-chip">⌁ 24H time</span>
              <span class="v96-chip">🔒 Local intelligence</span>
            </div>
          </div>
          <div class="v96-score-wrap">
            <div class="v96-score-ring" style="--score:{_v96_health:.0f};">
              <div><b>{_v96_health:.0f}</b><span>/100</span></div>
            </div>
            <small>HR HEALTH SCORE</small>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="v96-section-head"><span>AI PRIORITY QUEUE</span><small>Automatically ranked from live HR signals</small></div>', unsafe_allow_html=True)
    _v96_cols = st.columns(3, gap="small")
    for _v96_i, (_v96_level, _v96_title, _v96_detail, _v96_target) in enumerate(_v96_priorities[:3]):
        with _v96_cols[_v96_i]:
            _v96_level_class = _v96_level.lower().replace(" ", "-")
            st.markdown(
                f"""
                <div class="v96-priority-card">
                  <div class="v96-priority-top"><span class="v96-level {_v96_level_class}">{_v96_level}</span><span>0{_v96_i+1}</span></div>
                  <div class="v96-priority-title">{html.escape(_v96_title)}</div>
                  <div class="v96-priority-copy">{html.escape(_v96_detail)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if _v96_target in available_modules and _v96_target != "Home":
                if st.button(f"Open {_v96_target}", key=f"v96_home_priority_{_v96_i}", use_container_width=True):
                    st.session_state["_v83_nav_request"] = _v96_target
                    st.rerun()

''' + home_anchor
replace_once(home_anchor, home_block, "home AI command centre")

# ---------------------------------------------------------------------
# MANAGEMENT: executive AI pulse before the MIS report hub.
# ---------------------------------------------------------------------
mgmt_anchor = '''    if global_division not in (ALL_DIVISIONS,"Greater Noida Plant"):
        contractor = contractor.iloc[0:0]

    # V9.3 MANAGEMENT MIS CENTRE'''
mgmt_new = r'''    if global_division not in (ALL_DIVISIONS,"Greater Noida Plant"):
        contractor = contractor.iloc[0:0]

    # V9.6 executive pulse: read-only management decision support.
    _v96_m_active = len(emp_all)
    _v96_m_present = int((att["status"] == "Present").sum()) if not att.empty else 0
    _v96_m_review = int((att["status"] == "HR Review").sum()) if not att.empty else 0
    _v96_m_att_rate = (_v96_m_present / _v96_m_active * 100.0) if _v96_m_active else 0.0
    _v96_m_blockers = int(
        ((pay["Missing Days"] > 0) | (pay["HR Review"] > 0)).sum()
    ) if not pay.empty else 0
    _v96_m_score = max(
        0.0,
        min(100.0, _v96_m_att_rate - min(25.0, _v96_m_review * 0.7 + _v96_m_blockers * 0.25)),
    )
    st.markdown(
        f"""
        <div class="v96-exec-pulse">
          <div><small>AI EXECUTIVE PULSE</small><b>{_v96_m_score:.0f}/100</b><span>Operational workforce score</span></div>
          <div><small>ATTENDANCE</small><b>{_v96_m_att_rate:.1f}%</b><span>{_v96_m_present:,} present / {_v96_m_active:,} active</span></div>
          <div><small>HR SIGNALS</small><b>{_v96_m_review:,}</b><span>Selected-date review rows</span></div>
          <div><small>PAYROLL GATES</small><b>{_v96_m_blockers:,}</b><span>Employees blocking close</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # V9.3 MANAGEMENT MIS CENTRE'''
replace_once(mgmt_anchor, mgmt_new, "management executive pulse")

# ---------------------------------------------------------------------
# AI TOOLS: stronger command-centre summary.
# ---------------------------------------------------------------------
ai_start = s.find('elif page == "AI Tools":')
if ai_start < 0:
    raise RuntimeError("AI Tools section not found")
ai_cards_anchor = '''    st.markdown(
        '<div class="v8-ai-grid">'''
ai_cards_pos = s.find(ai_cards_anchor, ai_start)
if ai_cards_pos < 0:
    raise RuntimeError("AI card anchor not found")
ai_command = r'''    # V9.6 AI COMMAND CENTRE
    _v96_ai_active = len(ai_emp)
    _v96_ai_present_rows = int((ai_att["status"] == "Present").sum()) if not ai_att.empty else 0
    _v96_ai_row_rate = (_v96_ai_present_rows / len(ai_att) * 100.0) if len(ai_att) else 0.0
    _v96_ai_risk = (
        (ai_hr_review * 3)
        + (ai_pay_blocked * 4)
        + (ai_salary_missing * 2)
        + (ai_dept_pending * 2)
    )
    _v96_ai_risk_label = "LOW" if _v96_ai_risk == 0 else "MODERATE" if _v96_ai_risk < 30 else "HIGH"
    _v96_ai_automation_ready = int(
        not _v94_upload_pending
        and _v94_master_pending == 0
        and _v94_review == 0
        and _v94_missing == 0
    )
    st.markdown(
        f"""
        <div class="v96-ai-console">
          <div class="v96-ai-console-left">
            <div class="v96-kicker">NEURAL WORKFORCE CONSOLE · LOCAL MODE</div>
            <h3>AI-assisted HR decisions without exporting company data</h3>
            <p>Live database signals are converted into prioritized actions, payroll gates, data-quality checks and management insights.</p>
          </div>
          <div class="v96-ai-console-grid">
            <div><small>RISK INDEX</small><b>{_v96_ai_risk_label}</b></div>
            <div><small>PAYROLL BLOCKERS</small><b>{ai_pay_blocked:,}</b></div>
            <div><small>30D HR REVIEW</small><b>{ai_hr_review:,}</b></div>
            <div><small>AUTOMATION GATE</small><b>{"READY" if _v96_ai_automation_ready else "BLOCKED"}</b></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

'''
s = s[:ai_cards_pos] + ai_command + s[ai_cards_pos:]

# Add a fifth AI tab dedicated to automation/readiness.
replace_once(
    '''    tab1,tab2,tab3,tab4 = st.tabs(
        ["Workforce Visualizer","Attendance Intelligence","Payroll Risk","Ask HR Data"]
    )''',
    '''    tab1,tab2,tab3,tab4,tab5 = st.tabs(
        ["Workforce Visualizer","Attendance Intelligence","Payroll Risk","Ask HR Data","Automation Hub"]
    )''',
    "AI tabs",
)

master_marker = '''# ============================================================
# MASTER CENTRE — ALL BUSINESS MASTERS IN ONE ADMIN WORKSPACE
# ============================================================
elif page == "Master Centre":'''
if master_marker not in s:
    raise RuntimeError("Master Centre marker not found")
automation_tab = r'''
    with tab5:
        st.markdown('<div class="v96-section-head"><span>AUTOMATION HUB</span><small>Live readiness gates · no silent data edits</small></div>', unsafe_allow_html=True)

        _v96_auto_rows = [
            ("Attendance source", "READY" if not _v94_upload_pending else "ACTION", "Attendance exists for the selected working date" if not _v94_upload_pending else "Attendance upload is required"),
            ("HR Review", "READY" if _v94_review == 0 else "ACTION", "No review rows in the current month" if _v94_review == 0 else f"{_v94_review:,} attendance review row(s) pending"),
            ("Employee Master", "READY" if _v94_master_pending == 0 else "ACTION", "No temporary HR Review department mappings" if _v94_master_pending == 0 else f"{_v94_master_pending:,} master record(s) pending"),
            ("Missing attendance", "READY" if _v94_missing == 0 else "CHECK", "No active employee is missing the selected-date row" if _v94_missing == 0 else f"{_v94_missing:,} active employee(s) need source verification"),
            ("Payroll close", "READY" if not _v94_payroll_pending else "CHECK", "Selected payroll context is finalized" if not _v94_payroll_pending else f"{global_payroll_month.strftime('%b %Y')} is not fully finalized"),
        ]
        for _v96_auto_name, _v96_auto_state, _v96_auto_detail in _v96_auto_rows:
            _v96_state_cls = _v96_auto_state.lower()
            st.markdown(
                f"""
                <div class="v96-auto-row">
                  <div><span class="v96-auto-dot {_v96_state_cls}"></span><b>{html.escape(_v96_auto_name)}</b></div>
                  <div>{html.escape(_v96_auto_detail)}</div>
                  <strong class="{_v96_state_cls}">{_v96_auto_state}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

        _v96_ready_count = sum(1 for _, state, _ in _v96_auto_rows if state == "READY")
        st.progress(_v96_ready_count / len(_v96_auto_rows), text=f"Automation readiness · {_v96_ready_count}/{len(_v96_auto_rows)} controls ready")
        st.caption(
            "Automation Hub is intentionally safe: it detects and routes work but does not silently mark attendance, change employee masters, or finalize payroll."
        )

        _v96_a1, _v96_a2, _v96_a3 = st.columns(3)
        if "Attendance" in available_modules and _v96_a1.button("Resolve Attendance", use_container_width=True, key="v96_auto_att"):
            st.session_state["_v83_nav_request"] = "Attendance"
            st.rerun()
        if "Employees" in available_modules and _v96_a2.button("Check Employee Master", use_container_width=True, key="v96_auto_emp"):
            st.session_state["_v83_nav_request"] = "Employees"
            st.rerun()
        if "Payroll" in available_modules and _v96_a3.button("Check Payroll", use_container_width=True, key="v96_auto_pay"):
            st.session_state["_v83_nav_request"] = "Payroll"
            st.rerun()

''' + master_marker
replace_once(master_marker, automation_tab, "Automation Hub tab")

# ---------------------------------------------------------------------
# Designer layer: premium command-centre visuals. UI only.
# ---------------------------------------------------------------------
designer_css = r'''

# ============================================================
# V9.6 DESIGNER / AI COMMAND CENTRE VISUAL LAYER
# No database, payroll, attendance or master mutations.
# ============================================================
st.markdown("""
<style>
@keyframes v96Glow {
  0%,100%{box-shadow:0 0 0 rgba(69,179,255,0)}
  50%{box-shadow:0 0 34px rgba(69,179,255,.10)}
}
@keyframes v96Scan {
  0%{transform:translateX(-120%)}
  100%{transform:translateX(220%)}
}
@keyframes v96PulseDot {
  0%,100%{opacity:.45;transform:scale(.82)}
  50%{opacity:1;transform:scale(1.18)}
}

.stApp{
  background:
    radial-gradient(circle at 80% 0%,rgba(43,117,190,.075),transparent 25%),
    radial-gradient(circle at 20% 14%,rgba(82,67,181,.055),transparent 22%),
    linear-gradient(180deg,#070c13 0%,#08101a 55%,#070c13 100%)!important;
}
.stApp:after{
  content:"";
  position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:
    linear-gradient(rgba(99,155,214,.022) 1px,transparent 1px),
    linear-gradient(90deg,rgba(99,155,214,.018) 1px,transparent 1px);
  background-size:48px 48px;
  mask-image:linear-gradient(to bottom,rgba(0,0,0,.55),transparent 70%);
}
.main .block-container{position:relative;z-index:1}

.v83-live-strip{
  border:1px solid rgba(71,127,188,.22)!important;
  background:linear-gradient(90deg,rgba(10,22,37,.96),rgba(12,28,45,.94),rgba(10,22,37,.96))!important;
  box-shadow:0 12px 32px rgba(0,0,0,.18)!important;
  backdrop-filter:blur(16px);
}

.v96-command-hero,
.v96-ai-console{
  position:relative;
  overflow:hidden;
  border:1px solid rgba(75,148,221,.30);
  background:
    radial-gradient(circle at 88% 12%,rgba(69,179,255,.14),transparent 26%),
    linear-gradient(135deg,rgba(15,31,49,.98),rgba(8,18,30,.99));
  border-radius:22px;
  padding:22px 24px;
  margin:10px 0 16px;
  box-shadow:0 24px 60px rgba(0,0,0,.22),inset 0 1px 0 rgba(255,255,255,.035);
  animation:v96Glow 5s ease-in-out infinite;
}
.v96-command-hero:before,
.v96-ai-console:before{
  content:"";
  position:absolute;top:0;left:0;width:38%;height:1px;
  background:linear-gradient(90deg,transparent,#6dc8ff,transparent);
  animation:v96Scan 5.5s linear infinite;
}
.v96-command-hero{display:flex;align-items:center;justify-content:space-between;gap:26px}
.v96-command-copy{min-width:0}
.v96-kicker{
  color:#72caff;font-size:10px;font-weight:950;letter-spacing:1.7px;
  margin-bottom:8px;
}
.v96-command-title{font-size:26px;font-weight:950;color:#fff;letter-spacing:-.5px}
.v96-command-title span{
  color:#8dd8ff;
  text-shadow:0 0 18px rgba(88,186,247,.22);
}
.v96-command-sub{max-width:760px;color:#b8c8d9;font-size:12.5px;line-height:1.5;margin-top:7px}
.v96-chip-row{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}
.v96-chip{
  padding:6px 9px;border:1px solid rgba(91,145,201,.22);border-radius:999px;
  background:rgba(13,28,45,.72);color:#bcd2e6;font-size:9.5px;font-weight:800;
}
.v96-score-wrap{text-align:center;min-width:126px}
.v96-score-wrap small{display:block;margin-top:5px;color:#8ea8bf;font-size:8.5px;font-weight:900;letter-spacing:1.2px}
.v96-score-ring{
  --p:calc(var(--score) * 1%);
  width:104px;height:104px;border-radius:50%;
  display:grid;place-items:center;
  background:conic-gradient(#58baf7 var(--p),rgba(76,111,148,.16) 0);
  position:relative;
  box-shadow:0 0 35px rgba(88,186,247,.13);
}
.v96-score-ring:before{
  content:"";position:absolute;inset:8px;border-radius:50%;
  background:linear-gradient(145deg,#0c1928,#08121e);
  border:1px solid rgba(93,152,211,.18);
}
.v96-score-ring div{position:relative;z-index:1;display:flex;align-items:baseline;gap:2px}
.v96-score-ring b{font-size:27px;color:#fff}.v96-score-ring span{font-size:9px;color:#8da5ba}

.v96-section-head{
  display:flex;align-items:center;justify-content:space-between;gap:10px;
  margin:17px 0 9px;padding:0 2px;
}
.v96-section-head span{font-size:11px;font-weight:950;color:#ddecfb;letter-spacing:1.2px}
.v96-section-head small{font-size:9.5px;color:#7990a8}

.v96-priority-card{
  min-height:132px;padding:15px;border-radius:16px;
  border:1px solid rgba(59,103,149,.30);
  background:linear-gradient(145deg,rgba(14,28,44,.98),rgba(9,19,31,.98));
  box-shadow:0 14px 30px rgba(0,0,0,.14);
  transition:transform .18s ease,border-color .18s ease;
}
.v96-priority-card:hover{transform:translateY(-2px);border-color:rgba(88,186,247,.43)}
.v96-priority-top{display:flex;justify-content:space-between;align-items:center;color:#5e7891;font-size:9px;font-weight:900}
.v96-level{padding:4px 7px;border-radius:999px;border:1px solid rgba(255,255,255,.08);font-size:8px;letter-spacing:.9px}
.v96-level.high{color:#ffb5b5;background:rgba(239,83,80,.10);border-color:rgba(239,83,80,.22)}
.v96-level.medium{color:#ffd990;background:rgba(245,184,61,.10);border-color:rgba(245,184,61,.22)}
.v96-level.clear{color:#9ff0c0;background:rgba(34,197,94,.10);border-color:rgba(34,197,94,.22)}
.v96-priority-title{font-size:14px;font-weight:900;color:#f7fbff;margin-top:12px}
.v96-priority-copy{font-size:10.5px;line-height:1.42;color:#98aec2;margin-top:6px}

.v96-exec-pulse{
  display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;
  margin:8px 0 18px;
}
.v96-exec-pulse>div{
  border:1px solid rgba(58,104,151,.26);border-radius:15px;padding:13px 14px;
  background:linear-gradient(145deg,#0f1d2d,#0b1623);
}
.v96-exec-pulse small{display:block;color:#7592ad;font-size:8.5px;font-weight:950;letter-spacing:1px}
.v96-exec-pulse b{display:block;color:#fff;font-size:21px;margin-top:5px}
.v96-exec-pulse span{display:block;color:#8fa6ba;font-size:9.5px;margin-top:3px}

.v96-ai-console{display:grid;grid-template-columns:1.2fr .8fr;gap:20px;align-items:center}
.v96-ai-console h3{font-size:20px!important;margin:0 0 7px!important}
.v96-ai-console p{font-size:11.5px!important;color:#9fb4c8!important;max-width:700px}
.v96-ai-console-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.v96-ai-console-grid>div{
  padding:12px;border-radius:13px;border:1px solid rgba(61,111,160,.24);
  background:rgba(8,20,33,.72);
}
.v96-ai-console-grid small{display:block;color:#7590aa;font-size:8px;font-weight:900;letter-spacing:.9px}
.v96-ai-console-grid b{display:block;margin-top:4px;font-size:15px;color:#f5fbff}

.v96-auto-row{
  display:grid;grid-template-columns:minmax(170px,.7fr) 1.6fr 90px;gap:12px;align-items:center;
  padding:12px 14px;margin:7px 0;border:1px solid rgba(58,102,147,.24);
  border-radius:13px;background:linear-gradient(90deg,rgba(14,28,44,.95),rgba(9,19,31,.95));
}
.v96-auto-row>div:first-child{display:flex;align-items:center;gap:8px;color:#edf6ff;font-size:11.5px}
.v96-auto-row>div:nth-child(2){color:#94aabe;font-size:10.5px}
.v96-auto-row>strong{text-align:right;font-size:9px;letter-spacing:.8px}
.v96-auto-row strong.ready{color:#6ee7a5}.v96-auto-row strong.action{color:#ff9c9c}.v96-auto-row strong.check{color:#ffd27a}
.v96-auto-dot{width:7px;height:7px;border-radius:50%;display:inline-block;animation:v96PulseDot 2s ease-in-out infinite}
.v96-auto-dot.ready{background:#22c55e}.v96-auto-dot.action{background:#ef5350}.v96-auto-dot.check{background:#f5b83d}

div[data-testid="stVerticalBlockBorderWrapper"]{
  transition:border-color .18s ease,transform .18s ease,box-shadow .18s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover{
  border-color:#294d73!important;
  box-shadow:0 18px 42px rgba(0,0,0,.20)!important;
}
.stButton button{
  border-radius:11px!important;
  transition:transform .14s ease,box-shadow .14s ease,border-color .14s ease!important;
}
.stButton button:hover{
  transform:translateY(-1px);
  border-color:#376a9d!important;
  box-shadow:0 8px 20px rgba(0,0,0,.18)!important;
}
[data-testid="stTabs"] [role="tablist"]{
  gap:4px;border-bottom:1px solid rgba(65,104,145,.22);
}
[data-testid="stTabs"] button[aria-selected="true"]{
  background:rgba(47,111,235,.12)!important;
  border-radius:10px 10px 0 0!important;
}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:has(input:checked){
  position:relative;
}
section[data-testid="stSidebar"] div[role="radiogroup"]>label:has(input:checked):before{
  content:"";position:absolute;left:0;top:8px;bottom:8px;width:3px;border-radius:4px;
  background:#6bc8ff;box-shadow:0 0 12px rgba(107,200,255,.55);
}

@media(max-width:1100px){
  .v96-command-hero{align-items:flex-start}
  .v96-exec-pulse{grid-template-columns:1fr 1fr}
  .v96-ai-console{grid-template-columns:1fr}
}
@media(max-width:760px){
  .v96-command-hero{display:block}
  .v96-score-wrap{margin-top:16px;text-align:left}
  .v96-exec-pulse{grid-template-columns:1fr}
  .v96-auto-row{grid-template-columns:1fr}
  .v96-auto-row>strong{text-align:left}
}
</style>
""", unsafe_allow_html=True)
'''

s += designer_css
p.write_text(s, encoding="utf-8")
print("Applied V9.6 designer + AI automation command centre")
