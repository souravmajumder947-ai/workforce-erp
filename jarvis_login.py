"""JARVIS login presentation using the application's existing authentication."""
import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


STYLE = """
<style>
body:has(.jarvis-login-root) [data-testid="stSidebar"] {display:none!important}
body:has(.jarvis-login-root) [data-testid="stAppViewContainer"] {
 background:radial-gradient(ellipse at 90% 10%,#10455855,transparent 60%),#04121f!important;
}
html body:has(.jarvis-login-root) header[data-testid="stHeader"] {
 height:3rem!important;min-height:3rem!important;background:#04121ff2!important;
}
html body:has(.jarvis-login-root) [data-testid="stMain"] .block-container {
 box-sizing:border-box!important;width:100%!important;max-width:1550px!important;
 margin:auto!important;padding:4.25rem 1.5rem 2rem!important;min-width:0!important;
}
body:has(.jarvis-login-root) [data-testid="stHorizontalBlock"] {
 gap:1.5rem!important;align-items:center!important;min-width:0!important;
}
body:has(.jarvis-login-root) [data-testid="stColumn"] {min-width:0!important}
body:has(.jarvis-login-root) .st-key-jarvis_login_card {
 background:linear-gradient(145deg,#123b4c99,#081d30d9)!important;
 border:1px solid #4ba4ba77!important;border-radius:22px!important;
 padding:clamp(20px,3vw,40px)!important;box-shadow:0 20px 65px #0005,inset 0 1px #c5f4ff22;
}
.jarvis-login-brand {display:flex;gap:18px;align-items:center;margin-bottom:22px}
.jarvis-login-brand img {width:45px;height:76px;object-fit:contain}
.jarvis-login-brand strong {color:#eefbff;font-size:clamp(21px,2vw,30px);line-height:1.2;display:block}
.jarvis-login-brand small {color:#9dd6e1;display:block;letter-spacing:.22em;margin-top:7px;font-size:11px}
.jarvis-login-title {color:#effcff;font-size:32px;font-weight:750;letter-spacing:-.03em;margin-bottom:20px}
.jarvis-login-footer {font-size:11px;color:#aac2d1;text-align:center;border-top:1px solid #36607577;padding-top:18px;margin-top:24px}
html body:has(.jarvis-login-root) .st-key-jarvis_login_card [data-testid="stForm"] {
 padding:0!important;border:0!important;background:transparent!important;
}
html body:has(.jarvis-login-root) .st-key-jarvis_login_card [data-testid="stWidgetLabel"] p {
 color:#dceef7!important;font-size:14px!important;font-weight:650!important;
}
html body:has(.jarvis-login-root) .st-key-jarvis_login_card [data-baseweb="input"] {
 background:#071d2ec9!important;border:1px solid #5899b077!important;border-radius:10px!important;
}
html body:has(.jarvis-login-root) .st-key-jarvis_login_card input {
 min-height:46px!important;background:transparent!important;color:#edfbff!important;font-size:15px!important;
}
html body:has(.jarvis-login-root) .st-key-jarvis_login_card button[kind="primaryFormSubmit"] {
 background:linear-gradient(100deg,#18e3e7,#4acfff)!important;color:#05283b!important;
 min-height:48px!important;border:0!important;border-radius:10px!important;margin-top:12px!important;
}
html body:has(.jarvis-login-root) .st-key-jarvis_login_card button[kind="primaryFormSubmit"] p {
 color:#05283b!important;font-size:15px!important;font-weight:800!important;
}
.jarvis-login-orb {height:100px;display:flex;justify-content:center;align-items:center;margin-top:22px}
.jarvis-login-orb b {position:relative;width:86px;height:86px;border:1px solid #39c3d7;border-radius:50%;
 display:grid;place-items:center;color:#d8fbff;box-shadow:0 0 26px #0dd9f233;font-size:12px;letter-spacing:.09em}
.jarvis-login-orb b:before,.jarvis-login-orb b:after {content:"";position:absolute;inset:-7px;border:2px solid transparent;
 border-top-color:#2de3ee;border-right-color:#2de3ee66;border-radius:50%;animation:jarvisLoginSpin 7s linear infinite}
.jarvis-login-orb b:after {inset:6px;border-top-color:#4daeff;animation-direction:reverse;animation-duration:12s}
@keyframes jarvisLoginSpin {to{transform:rotate(360deg)}}
@media(max-width:850px) {
 body:has(.jarvis-login-root) [data-testid="stHorizontalBlock"] {flex-direction:column!important}
 body:has(.jarvis-login-root) [data-testid="stColumn"] {width:100%!important;flex:1 1 100%!important}
 html body:has(.jarvis-login-root) [data-testid="stMain"] .block-container {padding:4rem 1rem 1.5rem!important}
 body:has(.jarvis-login-root) [data-testid="stColumn"]:first-child iframe {height:444px!important}
}
@media(prefers-reduced-motion:reduce) {.jarvis-login-orb b:before,.jarvis-login-orb b:after{animation:none!important}}
</style>
"""


@st.cache_data(show_spinner=False)
def factory_data_uri():
    image = Path(__file__).parent / "assets" / "jarvis_factory.webp"
    return "data:image/webp;base64," + base64.b64encode(image.read_bytes()).decode("ascii")


def render_factory():
    source = factory_data_uri()
    components.html(
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
        <style>
        *{box-sizing:border-box}body{margin:0;background:#04121f;color:#e1faff;font-family:system-ui,sans-serif}
        .camera{position:relative;height:calc(100vh - 4px);border:1px solid #398fa9;border-radius:22px;overflow:hidden;background:#061726}
        .factory{position:absolute;inset:-2%;background-image:url('""" + source + """');background-size:cover;background-position:center 50%;
        animation:factoryPan 18s ease-in-out infinite alternate;transform-origin:50% 55%;transition:background-position .5s}
        .camera.detail .factory{background-size:auto 135%;background-position:52% 44%}
        .camera.conveyor .factory{background-size:auto 155%;background-position:65% 65%}
        .shade{position:absolute;inset:0;background:linear-gradient(180deg,#04121ff0,transparent 25%,transparent 70%,#04121ff2);pointer-events:none}
        .heading{position:absolute;top:25px;left:24px;right:24px}
        .heading h2{font-size:clamp(23px,4vw,34px);letter-spacing:-.03em;margin:0 0 12px}
        .meta{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:11px;color:#b1d2e1}
        .tag{border:1px solid #3094a4;border-radius:30px;padding:5px 8px;color:#9be8e8}
        time{font-variant-numeric:tabular-nums}
        .scan{position:absolute;left:0;right:0;height:1px;background:#59eef432;box-shadow:0 0 20px #59eef440;
        animation:factoryScan 9s linear infinite;pointer-events:none}
        .controls{position:absolute;bottom:24px;left:24px;right:24px;display:flex;gap:8px;flex-wrap:wrap}
        button{cursor:pointer;background:#082337dc;color:#d3ebf5;border:1px solid #4c839d88;border-radius:9px;padding:10px 12px;font:12px system-ui}
        button[aria-pressed=true]{background:#14515c;border-color:#44e9f1}
        button:focus-visible{outline:3px solid #91f6fa;outline-offset:3px}
        .paused *{animation-play-state:paused!important}
        @keyframes factoryPan{from{transform:scale(1)}to{transform:scale(1.055)}}
        @keyframes factoryScan{from{top:15%}to{top:85%}}
        @media(max-width:500px){.camera{height:440px}.heading{top:18px;left:18px}.controls{left:18px;bottom:18px}}
        @media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}.scan{display:none}}
        </style>
        <div class="camera" id="camera"><div class="factory"></div><div class="shade"></div><div class="scan"></div>
        <div class="heading"><h2>Workforce &amp; operations</h2><div class="meta"><span class="tag">Animated demo</span>
        <span>Generated factory scene</span><time id="time">IST</time></div></div>
        <div class="controls"><button data-view="" aria-pressed="true">Factory view</button>
        <button data-view="detail" aria-pressed="false">Machine detail</button>
        <button data-view="conveyor" aria-pressed="false">Conveyor detail</button>
        <button id="pause" aria-pressed="false">Pause</button></div></div>
        <script>
        const camera=document.getElementById('camera'),clock=document.getElementById('time');
        function tick(){clock.textContent=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',hour:'2-digit',
        minute:'2-digit',second:'2-digit',hour12:false}).format(new Date())+' IST'}
        tick();setInterval(tick,1000);
        document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{
          camera.className='camera '+button.dataset.view;
          document.querySelectorAll('[data-view]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));
        }));
        document.getElementById('pause').addEventListener('click',function(){
          const paused=document.body.classList.toggle('paused');this.textContent=paused?'Play':'Pause';this.setAttribute('aria-pressed',String(paused));
        });
        </script></html>""",
        height=684,
        scrolling=False,
    )


def render_login(logo):
    st.markdown('<span class="jarvis-login-root"></span>', unsafe_allow_html=True)
    st.html(STYLE)
    factory, form = st.columns([1.15, 1], gap="large")
    with factory:
        render_factory()
    with form:
        with st.container(key="jarvis_login_card"):
            st.markdown(
                f'<div class="jarvis-login-brand"><img src="{logo}" alt="Reliable Packaging emblem">'
                '<div><strong>RELIABLE PACKAGING</strong><small>INDUSTRIES LIMITED</small></div></div>'
                '<div class="jarvis-login-title">Workforce ERP</div>',
                unsafe_allow_html=True,
            )
            with st.form("login_form_v82", clear_on_submit=False, border=False):
                username = st.text_input("User ID / Username", placeholder="Enter your user ID or username", autocomplete="username")
                password = st.text_input("Password", type="password", placeholder="Enter your password", autocomplete="current-password")
                submitted = st.form_submit_button("Sign In  →", type="primary", width="stretch")
            st.markdown(
                '<div class="jarvis-login-orb"><b>JARVIS</b></div>'
                '<div class="jarvis-login-footer">Created by Sourav Majumder</div>',
                unsafe_allow_html=True,
            )
    return username, password, submitted
