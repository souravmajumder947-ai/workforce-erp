from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V10.2 LIVE LOGIN EXPERIENCE"
if MARK in s:
    print("V10.2 login patch already applied")
    raise SystemExit(0)

old_cols = '    left_col, right_col = st.columns([1.20, .80], gap="medium")'
new_cols = '    left_col, right_col = st.columns([1.16, .84], gap="medium")'
if old_cols not in s:
    raise RuntimeError("Login column anchor not found")
s = s.replace(old_cols, new_cols, 1)

old_hero = '''            <div class="v82-ref-hero">
              <div class="v82-hero-canvas" style="background-image:url('{V82_LOGIN_HERO_DATA_URI}');">
                <div class="v83-cover-top-brand"></div>
                <div class="v83-hero-live"><span class="v83-live-pill"><span class="v83-live-dot"></span>LIVE HR SYSTEM</span></div>
                <div class="v90-hero-telemetry"><b>SMART FACTORY NETWORK</b><span class="v90-signal-bars"><i></i><i></i><i></i></span><span class="v92-live-sync" data-v92-live-sync>SYNC {_login_verified_time}</span></div>
                <div class="v94-map-location v95-map-cluster" aria-label="Three live company locations">
                  <span class="v95-location-dot one"></span><span class="v95-location-dot two"></span><span class="v95-location-dot three"></span>
                </div>
                <div class="v83-hero-ai-core"></div>
                <div class="v90-glass-sheen"></div>
                <div class="v90-data-rail one"></div>
                <div class="v90-data-rail two"></div>
                <div class="v82-ref-badge"><span class="flag">🇮🇳</span><span><b>Built in India</b>for modern manufacturing teams</span></div>
                <div class="v82-ref-credit">© 2026 Reliable Packaging HRMS · Created by Sourav Majumder</div>
              </div>
            </div>'''
new_hero = '''            <div class="v82-ref-hero">
              <div class="v82-hero-canvas v102-hero-canvas" style="background-image:url('{V82_LOGIN_HERO_DATA_URI}');">
                <div class="v102-hero-brand">
                  <img src="{LOGO_ICON_DATA_URI}" alt="Reliable Packaging">
                  <div><b>RELIABLE PACKAGING</b><strong>INDUSTRIES LIMITED</strong><small>WE PACK A BETTER TOMORROW</small></div>
                </div>
                <div class="v102-hero-copy">
                  <div class="v102-kicker">AI-POWERED HRMS COMMAND CENTRE</div>
                  <h1>Welcome back</h1>
                  <p>Live workforce intelligence for people, attendance, payroll and operations.</p>
                </div>
                <div class="v102-feature-strip">
                  <div><span>◉</span><b>LIVE DATABASE</b><small>Real-time HR data</small></div>
                  <div><span>✦</span><b>AI READY</b><small>Smart decision support</small></div>
                  <div><span>◈</span><b>SECURE ACCESS</b><small>Role-based protection</small></div>
                </div>
                <div class="v102-location-caption">
                  <b>OUR LOCATIONS</b>
                  <span>Greater Noida · D-63 Head Office · Dhaulana</span>
                </div>
                <div class="v83-cover-top-brand"></div>
                <div class="v83-hero-live"><span class="v83-live-pill"><span class="v83-live-dot"></span>SYSTEM ONLINE</span></div>
                <div class="v90-hero-telemetry"><b>SMART FACTORY NETWORK</b><span class="v90-signal-bars"><i></i><i></i><i></i></span><span class="v92-live-sync" data-v92-live-sync>SYNC {_login_verified_time}</span></div>
                <div class="v94-map-location v95-map-cluster" aria-label="Three live company locations">
                  <span class="v95-location-dot one"></span><span class="v95-location-dot two"></span><span class="v95-location-dot three"></span>
                </div>
                <div class="v83-hero-ai-core"></div>
                <div class="v90-glass-sheen"></div>
                <div class="v90-data-rail one"></div>
                <div class="v90-data-rail two"></div>
                <div class="v82-ref-badge"><span class="flag">🇮🇳</span><span><b>Made in India</b>for a stronger tomorrow</span></div>
                <div class="v82-ref-credit">People · Process · Performance · Possibilities</div>
              </div>
            </div>'''
if old_hero not in s:
    raise RuntimeError("Login hero markup anchor not found")
s = s.replace(old_hero, new_hero, 1)

old_card_head = '''                <div class="v90-auth-head">
                  <div class="v90-auth-orb">AI</div>
                  <div>
                    <div class="v90-card-kicker">Reliable workforce cloud</div>
                    <div class="v90-card-title">Welcome back</div>
                  </div>
                </div>
                <div class="v90-card-sub">Sign in to access live workforce intelligence, attendance, payroll and operations.</div>

                <div class="v92-company-brand">
                  <div class="v92-company-name">Reliable Packaging Industries Limited</div>
                  <div class="v92-company-slogan">WE KNOW YOUR REPUTATION IS IN OUR BOX</div>
                  <div class="v92-company-meta">Smart Manufacturing · Workforce · Payroll · Operations</div>
                </div>
                <div class="v90-status-grid">
                  <div class="v90-status active"><b><i class="v90-status-dot"></i>LIVE DATABASE</b><span>PostgreSQL services ready</span><small>Verified {_login_verified_time}</small></div>
                  <div class="v90-status"><b>✦ AI READY</b><span>HR intelligence online</span><small>Live decision support</small></div>
                  <div class="v90-status"><b>◈ SECURE</b><span>Role-based protection</span><small>Encrypted access</small></div>
                </div>'''
new_card_head = '''                <div class="v102-security-bar">
                  <div><i></i><span><b>ENTERPRISE GRADE SECURITY</b><small>All systems operational</small></span></div>
                  <strong data-v102-login-clock>{_login_verified_time}</strong>
                </div>
                <div class="v90-auth-head v102-auth-head">
                  <div class="v90-auth-orb">AI</div>
                  <div>
                    <div class="v90-card-kicker">Reliable Workforce Cloud</div>
                    <div class="v90-card-title">Sign in to your account</div>
                  </div>
                </div>
                <div class="v90-card-sub">Access live workforce intelligence, attendance, payroll and operations.</div>
                <div class="v102-brand-line">
                  <b>RELIABLE PACKAGING INDUSTRIES LIMITED</b>
                  <span>Smart HRMS · People · Process · Performance</span>
                </div>
                <div class="v90-status-grid v102-status-grid">
                  <div class="v90-status active"><b><i class="v90-status-dot"></i>LIVE DATABASE</b><span>PostgreSQL connected</span><small>Real-time source</small></div>
                  <div class="v90-status"><b>✦ AI READY</b><span>HR intelligence online</span><small>Decision support</small></div>
                  <div class="v90-status"><b>◈ SECURE</b><span>Role-based access</span><small>Protected session</small></div>
                </div>
                <div class="v102-login-locations">
                  <span><i class="one"></i>Greater Noida</span>
                  <span><i class="two"></i>D-63 Head Office</span>
                  <span><i class="three"></i>Dhaulana</span>
                </div>'''
if old_card_head not in s:
    raise RuntimeError("Login card intro anchor not found")
s = s.replace(old_card_head, new_card_head, 1)

old_footer = '''                <div class="v82-card-footer">Reliable Packaging Industries Limited<br>Built in India 🇮🇳 · Created by <b>Sourav Majumder</b></div>'''
new_footer = '''                <div class="v82-card-footer v102-card-footer">
                  <span>◈ Secured by enterprise-grade role protection</span>
                  <b>Reliable Packaging Industries Limited</b>
                  <small>Built in India 🇮🇳 · Created by Sourav Majumder</small>
                </div>'''
if old_footer not in s:
    raise RuntimeError("Login footer anchor not found")
s = s.replace(old_footer, new_footer, 1)

bt = chr(96)
dollar = chr(36)
clock_anchor = '                  node.textContent = ' + bt + 'SYNC ' + dollar + '{clock.format(now)}' + bt + ';'
clock_new = '''                  node.textContent = "SYNC " + clock.format(now);
                  const loginClock = window.parent.document.querySelector("[data-v102-login-clock]");
                  if (loginClock) loginClock.textContent = clock.format(now);'''
if clock_anchor not in s:
    raise RuntimeError("Login clock script anchor not found")
s = s.replace(clock_anchor, clock_new, 1)

s += r'''

# ============================================================
# V10.2 LIVE LOGIN EXPERIENCE
# Designer / responsive / animated. Authentication logic unchanged.
# ============================================================
st.markdown("""
<style>
@keyframes v102BorderFlow{0%,100%{box-shadow:0 30px 80px rgba(0,0,0,.32),0 0 0 rgba(59,177,255,0)}50%{box-shadow:0 34px 90px rgba(0,0,0,.40),0 0 32px rgba(59,177,255,.10)}}
@keyframes v102HeroPulse{0%,100%{filter:brightness(.84) saturate(1.02)}50%{filter:brightness(.93) saturate(1.08)}}
@keyframes v102Float{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}
body:has(.v82-login-root) [data-testid="stAppViewContainer"]{
  background:radial-gradient(circle at 15% 10%,rgba(33,116,201,.12),transparent 24%),radial-gradient(circle at 82% 80%,rgba(91,55,196,.08),transparent 28%),linear-gradient(145deg,#030a13 0%,#06101c 52%,#040b14 100%)!important;
}
body:has(.v82-login-root) header[data-testid="stHeader"]{background:rgba(3,10,19,.84)!important;border-bottom:1px solid rgba(62,114,166,.13)!important}
body:has(.v82-login-root) .block-container{max-width:1740px!important;padding:.42rem 1.15rem .7rem!important}
body:has(.v82-login-root) div[data-testid="stHorizontalBlock"]{gap:1.05rem!important;align-items:stretch!important}
.v82-ref-hero{height:clamp(590px,calc(100dvh - 3.3rem),760px)!important;border-radius:22px!important;overflow:hidden!important;border:1px solid rgba(64,157,236,.26)!important;background:#030a13!important;box-shadow:0 30px 80px rgba(0,0,0,.34)!important}
.v102-hero-canvas{width:100%!important;height:100%!important;max-width:none!important;aspect-ratio:auto!important;background-size:cover!important;background-position:center 41%!important;animation:v102HeroPulse 8s ease-in-out infinite}
.v102-hero-canvas:after{content:"";position:absolute;inset:0;z-index:2;pointer-events:none;background:linear-gradient(90deg,rgba(2,8,17,.88) 0%,rgba(2,8,17,.62) 42%,rgba(2,8,17,.24) 72%,rgba(2,8,17,.46) 100%),linear-gradient(180deg,rgba(2,8,17,.28),transparent 35%,rgba(2,8,17,.58) 100%)}
.v102-hero-brand{position:absolute;z-index:12;left:28px;top:28px;display:grid;grid-template-columns:48px auto;gap:11px;align-items:center;padding:10px 13px 10px 10px;border-radius:14px;background:rgba(3,12,23,.68);border:1px solid rgba(82,164,235,.22);backdrop-filter:blur(14px);box-shadow:0 12px 28px rgba(0,0,0,.18)}
.v102-hero-brand img{width:44px;height:48px;object-fit:contain;filter:drop-shadow(0 0 12px rgba(255,92,54,.18))}
.v102-hero-brand b,.v102-hero-brand strong,.v102-hero-brand small{display:block;line-height:1.05}.v102-hero-brand b{font-size:12px;color:#fff;letter-spacing:.6px}.v102-hero-brand strong{font-size:12px;color:#ff623f;margin-top:3px}.v102-hero-brand small{font-size:7px;color:#a8bdd0;margin-top:7px;letter-spacing:1.15px}
.v102-hero-copy{position:absolute;z-index:12;left:30px;bottom:178px;max-width:560px}.v102-kicker{color:#6bd5ff;font-size:9px;font-weight:950;letter-spacing:1.5px;margin-bottom:8px}
.v102-hero-copy h1{margin:0!important;color:#fff!important;font-size:clamp(36px,3vw,58px)!important;line-height:1!important;text-shadow:0 8px 24px rgba(0,0,0,.35)}
.v102-hero-copy p{max-width:470px;margin:13px 0 0!important;color:#c2d2e1!important;font-size:12px!important;line-height:1.55!important}
.v102-feature-strip{position:absolute;z-index:12;left:28px;right:28px;bottom:76px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.v102-feature-strip>div{min-height:72px;padding:10px;border-radius:12px;background:linear-gradient(145deg,rgba(6,22,38,.80),rgba(4,14,27,.72));border:1px solid rgba(67,151,226,.24);backdrop-filter:blur(11px);box-shadow:0 10px 24px rgba(0,0,0,.14);transition:transform .18s ease,border-color .18s ease}
.v102-feature-strip>div:hover{transform:translateY(-2px);border-color:rgba(80,193,255,.45)}.v102-feature-strip span{display:block;color:#61d8ff;font-size:16px}.v102-feature-strip b{display:block;color:#e8f6ff;font-size:8.5px;margin-top:5px;letter-spacing:.7px}.v102-feature-strip small{display:block;color:#7893ac;font-size:7px;margin-top:3px}
.v102-location-caption{position:absolute;z-index:12;right:27px;bottom:24px;text-align:right;padding:7px 10px;border-radius:10px;background:rgba(4,13,24,.60);border:1px solid rgba(67,136,202,.18);backdrop-filter:blur(10px)}
.v102-location-caption b,.v102-location-caption span{display:block}.v102-location-caption b{font-size:7px;color:#72d7ff;letter-spacing:1px}.v102-location-caption span{font-size:7px;color:#9eb0c2;margin-top:3px}
.v102-hero-canvas .v83-cover-top-brand{display:none!important}.v102-hero-canvas .v83-hero-live{left:auto!important;right:28px!important;top:28px!important;z-index:13!important}.v102-hero-canvas .v90-hero-telemetry{left:auto!important;right:28px!important;top:66px!important;z-index:13!important;justify-content:flex-end!important}
.v102-hero-canvas .v82-ref-badge{z-index:13!important;left:28px!important;bottom:20px!important;background:rgba(5,17,30,.62)!important;backdrop-filter:blur(10px)}.v102-hero-canvas .v82-ref-credit{display:none!important}.v102-hero-canvas .v83-hero-ai-core{z-index:11!important;right:16%!important;bottom:32%!important;opacity:.65!important}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.v82-login-card-marker){min-height:clamp(590px,calc(100dvh - 3.3rem),760px)!important;max-width:none!important;width:100%!important;margin:0!important;border-radius:22px!important;background:radial-gradient(circle at 92% 3%,rgba(102,69,224,.15),transparent 28%),radial-gradient(circle at 4% 96%,rgba(33,172,226,.07),transparent 28%),linear-gradient(155deg,rgba(10,26,45,.94),rgba(5,15,28,.97))!important;border:1px solid rgba(104,172,241,.30)!important;box-shadow:0 30px 80px rgba(0,0,0,.34),inset 0 1px 0 rgba(255,255,255,.04)!important;animation:v102BorderFlow 6s ease-in-out infinite!important}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.v82-login-card-marker)>div{padding:20px 24px 17px!important}
.v102-security-bar{min-height:50px;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:9px 11px;margin-bottom:18px;border-radius:12px;border:1px solid rgba(74,157,231,.22);background:rgba(5,18,32,.62)}
.v102-security-bar>div{display:flex;align-items:center;gap:9px}.v102-security-bar i{width:8px;height:8px;border-radius:50%;background:#2ed39a;box-shadow:0 0 14px rgba(46,211,154,.55);animation:v96PulseDot 1.8s ease-in-out infinite}.v102-security-bar b,.v102-security-bar small{display:block}.v102-security-bar b{font-size:8px;color:#98c6ef;letter-spacing:.8px}.v102-security-bar small{font-size:7px;color:#758da5;margin-top:2px}.v102-security-bar strong{font-size:10px;color:#a8c5de;letter-spacing:.5px;font-variant-numeric:tabular-nums}
.v102-auth-head{margin-bottom:4px!important}.v102-auth-head .v90-auth-orb{width:48px!important;height:48px!important;animation:v102Float 3s ease-in-out infinite}.v102-auth-head .v90-card-title{font-size:clamp(25px,1.55vw,38px)!important;line-height:1.05!important;margin-top:4px}.v102-auth-head .v90-card-kicker{font-size:10px!important;letter-spacing:1.35px!important}.v90-card-sub{margin:10px 0 15px!important;font-size:11px!important;line-height:1.45!important}
.v102-brand-line{padding:10px 12px;margin:0 0 13px;border-radius:11px;border:1px solid rgba(74,145,211,.18);background:linear-gradient(90deg,rgba(13,39,65,.66),rgba(7,21,38,.56))}.v102-brand-line b,.v102-brand-line span{display:block}.v102-brand-line b{font-size:9px;color:#eaf5ff;letter-spacing:.45px}.v102-brand-line span{font-size:7.4px;color:#7fa5c5;margin-top:4px}
.v102-status-grid{margin-bottom:10px!important}.v102-status-grid .v90-status{min-height:61px!important;padding:8px!important;border-radius:10px!important}.v102-status-grid .v90-status b{font-size:7.5px!important}.v102-status-grid .v90-status span{font-size:6.7px!important}.v102-status-grid .v90-status small{font-size:6.1px!important}
.v102-login-locations{display:flex;gap:6px;flex-wrap:wrap;margin:-1px 0 13px}.v102-login-locations span{display:flex;align-items:center;gap:5px;padding:5px 7px;border-radius:999px;border:1px solid rgba(70,132,193,.17);background:rgba(5,17,30,.50);color:#8fa9c0;font-size:6.8px;font-weight:700}.v102-login-locations i{width:6px;height:6px;border-radius:50%;display:inline-block}.v102-login-locations i.one{background:#2ed39a}.v102-login-locations i.two{background:#3498ff}.v102-login-locations i.three{background:#ff665f}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.v82-login-card-marker) [data-testid="stWidgetLabel"] p{font-size:11px!important;font-weight:850!important;color:#eaf3fb!important}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.v82-login-card-marker) input{min-height:45px!important;font-size:13px!important;border-radius:10px!important}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.v82-login-card-marker) button[kind="primaryFormSubmit"]{min-height:47px!important;border-radius:10px!important;background:linear-gradient(100deg,#2e75f0 0%,#526bea 55%,#7a4fe6 100%)!important;box-shadow:0 10px 24px rgba(58,90,222,.20)!important}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.v82-login-card-marker) button[kind="primaryFormSubmit"]:hover{transform:translateY(-1px);box-shadow:0 14px 30px rgba(58,102,238,.28)!important}
.v102-card-footer{margin-top:11px!important;padding-top:10px!important;border-top:1px solid rgba(73,120,165,.17);text-align:center!important}.v102-card-footer span,.v102-card-footer b,.v102-card-footer small{display:block}.v102-card-footer span{font-size:6.8px;color:#7895ad;margin-bottom:7px}.v102-card-footer b{font-size:7.5px;color:#a9bdcf}.v102-card-footer small{font-size:6.6px;color:#6f879e;margin-top:3px}
@media(max-height:760px){
  .v82-ref-hero,div[data-testid="stVerticalBlockBorderWrapper"]:has(.v82-login-card-marker){min-height:570px!important;height:570px!important}
  .v102-hero-copy{bottom:162px}.v102-feature-strip{bottom:68px}
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.v82-login-card-marker)>div{padding:15px 20px 13px!important}
  .v102-security-bar{margin-bottom:11px;min-height:42px}.v102-brand-line{padding:8px 10px;margin-bottom:9px}.v102-status-grid{margin-bottom:7px!important}.v102-login-locations{margin-bottom:8px}
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.v82-login-card-marker) input{min-height:40px!important}
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.v82-login-card-marker) button[kind="primaryFormSubmit"]{min-height:42px!important}
}
@media(max-width:1100px){body:has(.v82-login-root) div[data-testid="stHorizontalBlock"]{display:block!important}.v82-ref-hero{height:520px!important;margin-bottom:12px}div[data-testid="stVerticalBlockBorderWrapper"]:has(.v82-login-card-marker){min-height:auto!important}}
</style>
""", unsafe_allow_html=True)
'''

p.write_text(s, encoding="utf-8")
print("Applied V10.2 live login experience")
