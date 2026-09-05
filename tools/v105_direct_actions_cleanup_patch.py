from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V10.5 DIRECT ACTION CARDS + CLEAN LOGIN"
if MARK in s:
    print("V10.5 patch already applied")
    raise SystemExit(0)

# Remove the unnecessary location strip from the right-side login panel.
old_locations = '''                <div class="v103-location-strip">
                  <span><i class="g"></i>Greater Noida</span>
                  <span><i class="b"></i>D-63 Head Office</span>
                  <span><i class="r"></i>Dhaulana</span>
                </div>
'''
if old_locations not in s:
    raise RuntimeError("Right-side login location strip not found")
s = s.replace(old_locations, "", 1)

# Replace the two-level utility cards (visual tile + separate Open button)
# with one direct clickable control per function.
old_utils = '''    # Reference-style bottom utility rail, fully functional.
    _v10_u1, _v10_u2, _v10_u3, _v10_u4, _v10_u5 = st.columns(5, gap="small")
    _v10_utils = [
        (_v10_u1, "✦", "AI Assistant", "Ask anything about HR data", "AI Tools", "v10_util_ai"),
        (_v10_u2, "⚙", "Automation Hub", "Readiness & repetitive-work routing", "AI Tools", "v10_util_auto"),
        (_v10_u3, "▥", "Smart Reports", "Interactive MIS & insights", "Reports", "v10_util_reports"),
        (_v10_u4, "⇩", "Data Export", "Excel / PDF / report exports", "Reports", "v10_util_export"),
        (_v10_u5, "♥", "System Health", "Database and HR controls", "Management", "v10_util_health"),
    ]
    for _v10_col, _v10_icon, _v10_title, _v10_sub, _v10_target, _v10_key in _v10_utils:
        with _v10_col:
            st.markdown(
                f'<div class="v10-util-label"><span>{_v10_icon}</span><div><b>{_v10_title}</b><small>{_v10_sub}</small></div></div>',
                unsafe_allow_html=True,
            )
            if _v10_target in available_modules and st.button("Open", key=_v10_key, use_container_width=True):
                st.session_state["_v83_nav_request"] = _v10_target
                st.rerun()
'''
new_utils = '''    # V10.5 DIRECT ACTION CARDS + CLEAN LOGIN
    # One control = one action. No separate decorative card + Open button.
    st.markdown('<div class="v105-direct-action-marker"></div>', unsafe_allow_html=True)
    _v10_u1, _v10_u2, _v10_u3, _v10_u4, _v10_u5 = st.columns(5, gap="small")
    _v10_utils = [
        (_v10_u1, "✦  AI Assistant", "Ask anything about HR data", "AI Tools", "v10_util_ai"),
        (_v10_u2, "⚙  Automation Hub", "Readiness & repetitive-work routing", "AI Tools", "v10_util_auto"),
        (_v10_u3, "▥  Smart Reports", "Interactive MIS & insights", "Reports", "v10_util_reports"),
        (_v10_u4, "⇩  Data Export", "Excel / PDF / report exports", "Reports", "v10_util_export"),
        (_v10_u5, "♥  System Health", "Database and HR controls", "Management", "v10_util_health"),
    ]
    for _v10_col, _v10_label, _v10_sub, _v10_target, _v10_key in _v10_utils:
        with _v10_col:
            if _v10_target in available_modules:
                if st.button(
                    _v10_label,
                    key=_v10_key,
                    use_container_width=True,
                    help=_v10_sub,
                ):
                    st.session_state["_v83_nav_request"] = _v10_target
                    st.rerun()
            else:
                st.button(
                    _v10_label,
                    key=f"{_v10_key}_disabled",
                    use_container_width=True,
                    help="This module is not available for your current role.",
                    disabled=True,
                )
'''
if old_utils not in s:
    raise RuntimeError("Home utility rail block not found")
s = s.replace(old_utils, new_utils, 1)

# Append narrowly-scoped visual cleanup.
s += r'''

# ============================================================
# V10.5 DIRECT ACTION CARDS + CLEAN LOGIN
# ============================================================
st.markdown("""
<style>
/* Right-side login only: remove leftover location-chip spacing and Streamlit form hint. */
body:has(.v82-login-root) .v103-location-strip{display:none!important}
body:has(.v82-login-root) [data-testid="InputInstructions"]{display:none!important}
body:has(.v82-login-root) [data-testid="stForm"]{margin-top:4px!important}

/* Home utility controls are now the cards themselves. */
body:has(.v105-direct-action-marker) div[data-testid="stHorizontalBlock"]:has(button[key]){
  align-items:stretch!important;
}
body:has(.v105-direct-action-marker) .stButton>button{
  min-height:72px!important;
  height:72px!important;
  justify-content:flex-start!important;
  text-align:left!important;
  padding:13px 14px!important;
  border-radius:13px!important;
  border:1px solid rgba(57,125,191,.34)!important;
  background:
    radial-gradient(circle at 12% 25%,rgba(62,99,221,.20),transparent 34%),
    linear-gradient(145deg,#0b1c2d,#081522)!important;
  color:#eaf4ff!important;
  font-size:11px!important;
  font-weight:850!important;
  letter-spacing:.01em!important;
  box-shadow:0 10px 24px rgba(0,0,0,.13)!important;
  position:relative!important;
  overflow:hidden!important;
}
body:has(.v105-direct-action-marker) .stButton>button:after{
  content:"↗";
  position:absolute;
  right:13px;
  top:50%;
  transform:translateY(-50%);
  color:#6fbff3;
  font-size:14px;
  opacity:.78;
}
body:has(.v105-direct-action-marker) .stButton>button:not(:disabled):hover{
  transform:translateY(-2px)!important;
  border-color:rgba(83,174,255,.58)!important;
  background:
    radial-gradient(circle at 12% 25%,rgba(73,108,237,.27),transparent 36%),
    linear-gradient(145deg,#0f2740,#0a1a2b)!important;
  box-shadow:0 14px 30px rgba(0,0,0,.19),0 0 20px rgba(52,139,228,.07)!important;
}
body:has(.v105-direct-action-marker) .stButton>button:disabled:after{
  content:"🔒";
  opacity:.55;
}

/* Retire the old label styling if any stale DOM survives during hot reload. */
body:has(.v105-direct-action-marker) .v10-util-label{display:none!important}

@media(max-width:900px){
  body:has(.v105-direct-action-marker) .stButton>button{
    min-height:58px!important;height:58px!important;font-size:10px!important
  }
}
</style>
""", unsafe_allow_html=True)
'''

p.write_text(s, encoding="utf-8")
print("Applied V10.5 direct actions and login cleanup")
