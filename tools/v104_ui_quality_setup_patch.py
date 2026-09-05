from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V10.4 APP UI QUALITY + CONTROL AUDIT"
if MARK in s:
    print("V10.4 UI quality patch already applied")
    raise SystemExit(0)

# Logged-in-only quality marker. This lets the final CSS avoid touching the login page.
anchor = '''_current_user = st.session_state["auth_user"]
_current_role = str(_current_user.get("role", "Viewer"))'''
replacement = '''_current_user = st.session_state["auth_user"]
_current_role = str(_current_user.get("role", "Viewer"))
st.markdown('<div class="v104-app-quality-marker"></div>', unsafe_allow_html=True)'''
if anchor not in s:
    raise RuntimeError("Logged-in user anchor not found")
s = s.replace(anchor, replacement, 1)

# Attendance gets its own page marker and clearer tab labels.
anchor = '''elif page == "Attendance":
    v5_page_header("Attendance","Upload once, review exceptions, correct HR remarks and monitor monthly attendance.",global_division,global_work_date)
    tab_upload, tab_daily, tab_review, tab_month = st.tabs(["Upload","Daily Register","HR Review","Monthly Summary"])'''
replacement = '''elif page == "Attendance":
    st.markdown('<div class="v104-attendance-page"></div>', unsafe_allow_html=True)
    v5_page_header("Attendance","Upload once, review exceptions, correct HR remarks and monitor monthly attendance.",global_division,global_work_date)
    tab_upload, tab_daily, tab_review, tab_month = st.tabs(
        ["Upload Attendance","Daily Register","HR Review","Monthly Summary"]
    )'''
if anchor not in s:
    raise RuntimeError("Attendance tab anchor not found")
s = s.replace(anchor, replacement, 1)

# Final visual layer. It is deliberately scoped to logged-in pages only.
s += r'''

# ============================================================
# V10.4 APP UI QUALITY + CONTROL AUDIT
# Logged-in application only. Login screen is intentionally untouched.
# ============================================================
st.markdown("""
<style>
/* ------------------------------------------------------------
   GLOBAL LOGGED-IN VIEW QUALITY
   ------------------------------------------------------------ */
body:has(.v104-app-quality-marker) .block-container{
  padding-top:.7rem!important;
  padding-bottom:1.25rem!important;
}
body:has(.v104-app-quality-marker) h1,
body:has(.v104-app-quality-marker) h2,
body:has(.v104-app-quality-marker) h3{
  letter-spacing:-.015em;
}
body:has(.v104-app-quality-marker) [data-testid="stCaptionContainer"]{
  color:#8196aa!important;
}

/* Consistent tab/navigation treatment. Prevents tab text from touching. */
body:has(.v104-app-quality-marker) [data-testid="stTabs"]{
  margin-top:8px!important;
}
body:has(.v104-app-quality-marker) [data-testid="stTabs"] [role="tablist"]{
  display:flex!important;
  align-items:center!important;
  gap:9px!important;
  flex-wrap:wrap!important;
  padding:0 0 10px!important;
  margin:0 0 12px!important;
  border-bottom:1px solid rgba(70,116,160,.24)!important;
}
body:has(.v104-app-quality-marker) [data-testid="stTabs"] button[role="tab"]{
  flex:0 0 auto!important;
  min-height:38px!important;
  padding:8px 15px!important;
  margin:0!important;
  border:1px solid rgba(67,116,166,.22)!important;
  border-radius:10px!important;
  background:linear-gradient(145deg,rgba(11,28,46,.88),rgba(8,21,35,.88))!important;
  color:#9db1c4!important;
  transition:background .16s ease,border-color .16s ease,color .16s ease,transform .16s ease!important;
}
body:has(.v104-app-quality-marker) [data-testid="stTabs"] button[role="tab"] p{
  margin:0!important;
  padding:0!important;
  white-space:nowrap!important;
  font-size:12px!important;
  font-weight:760!important;
  line-height:1.1!important;
}
body:has(.v104-app-quality-marker) [data-testid="stTabs"] button[role="tab"]:hover{
  transform:translateY(-1px)!important;
  border-color:rgba(80,157,226,.42)!important;
  color:#d8ebfb!important;
  background:linear-gradient(145deg,rgba(17,45,72,.94),rgba(9,27,46,.94))!important;
}
body:has(.v104-app-quality-marker) [data-testid="stTabs"] button[role="tab"][aria-selected="true"]{
  color:#ffffff!important;
  border-color:rgba(79,165,255,.56)!important;
  background:linear-gradient(120deg,rgba(36,110,214,.72),rgba(21,76,143,.68))!important;
  box-shadow:0 7px 20px rgba(27,106,211,.15),inset 0 0 0 1px rgba(118,193,255,.12)!important;
}
body:has(.v104-app-quality-marker) [data-testid="stTabs"] button[role="tab"][aria-selected="true"]:after{
  display:none!important;
}

/* Buttons: consistent active/disabled visual states. */
body:has(.v104-app-quality-marker) .stButton>button,
body:has(.v104-app-quality-marker) .stDownloadButton>button,
body:has(.v104-app-quality-marker) button[kind="primaryFormSubmit"]{
  min-height:40px!important;
  border-radius:10px!important;
  font-weight:760!important;
  letter-spacing:.01em!important;
  transition:transform .14s ease,border-color .14s ease,box-shadow .14s ease,background .14s ease!important;
}
body:has(.v104-app-quality-marker) .stButton>button:not(:disabled):hover,
body:has(.v104-app-quality-marker) .stDownloadButton>button:not(:disabled):hover,
body:has(.v104-app-quality-marker) button[kind="primaryFormSubmit"]:not(:disabled):hover{
  transform:translateY(-1px)!important;
  box-shadow:0 9px 22px rgba(0,0,0,.18)!important;
}
body:has(.v104-app-quality-marker) button:disabled{
  opacity:.46!important;
  cursor:not-allowed!important;
  filter:saturate(.55)!important;
}
body:has(.v104-app-quality-marker) button:focus-visible,
body:has(.v104-app-quality-marker) input:focus-visible{
  outline:2px solid rgba(87,170,255,.55)!important;
  outline-offset:2px!important;
}

/* Inputs/selects/uploaders all sit on one design system. */
body:has(.v104-app-quality-marker) input,
body:has(.v104-app-quality-marker) textarea,
body:has(.v104-app-quality-marker) [data-baseweb="select"]>div{
  border-radius:10px!important;
}
body:has(.v104-app-quality-marker) [data-testid="stFileUploaderDropzone"]{
  border:1px dashed rgba(77,134,191,.38)!important;
  border-radius:12px!important;
  background:linear-gradient(145deg,rgba(11,27,45,.74),rgba(8,21,35,.74))!important;
  padding:12px!important;
}
body:has(.v104-app-quality-marker) [data-testid="stFileUploaderDropzone"]:hover{
  border-color:rgba(83,169,250,.58)!important;
}
body:has(.v104-app-quality-marker) [data-testid="stWidgetLabel"] p{
  font-weight:720!important;
}

/* Cards/containers get predictable breathing room. */
body:has(.v104-app-quality-marker) div[data-testid="stVerticalBlockBorderWrapper"]{
  border-radius:13px!important;
}
body:has(.v104-app-quality-marker) div[data-testid="stVerticalBlockBorderWrapper"]>div{
  row-gap:.65rem!important;
}

/* Tables and dataframe areas: clean edge alignment. */
body:has(.v104-app-quality-marker) [data-testid="stDataFrame"],
body:has(.v104-app-quality-marker) [data-testid="stTable"]{
  border-radius:11px!important;
  overflow:hidden!important;
}

/* ------------------------------------------------------------
   ATTENDANCE PAGE — SPECIFIC CLEANUP
   ------------------------------------------------------------ */
body:has(.v104-attendance-page) [data-testid="stTabs"]{
  margin-top:12px!important;
}
body:has(.v104-attendance-page) [data-testid="stTabs"] [role="tablist"]{
  gap:10px!important;
  padding-left:1px!important;
}
body:has(.v104-attendance-page) [data-testid="stTabs"] button[role="tab"]{
  min-width:126px!important;
  justify-content:center!important;
  padding-left:17px!important;
  padding-right:17px!important;
}
body:has(.v104-attendance-page) [data-testid="stTabs"] button[role="tab"]:first-child{
  min-width:145px!important;
}
body:has(.v104-attendance-page) [data-testid="stInfo"]{
  border-radius:10px!important;
}
body:has(.v104-attendance-page) [data-testid="stFileUploader"]{
  margin-top:3px!important;
}
body:has(.v104-attendance-page) [data-testid="stRadio"]{
  padding-top:1px!important;
}
body:has(.v104-attendance-page) .stDownloadButton{
  margin:5px 0 4px!important;
}

/* Keep page form rows aligned on typical laptops. */
@media(min-width:1000px){
  body:has(.v104-attendance-page) div[data-testid="stHorizontalBlock"]{
    column-gap:14px!important;
  }
}
@media(max-width:900px){
  body:has(.v104-app-quality-marker) [data-testid="stTabs"] [role="tablist"]{
    gap:6px!important;
  }
  body:has(.v104-app-quality-marker) [data-testid="stTabs"] button[role="tab"]{
    min-width:auto!important;
    padding:7px 10px!important;
  }
  body:has(.v104-app-quality-marker) [data-testid="stTabs"] button[role="tab"] p{
    font-size:11px!important;
  }
}
</style>
""", unsafe_allow_html=True)
'''

p.write_text(s, encoding="utf-8")
print("Applied V10.4 logged-in UI quality layer")
