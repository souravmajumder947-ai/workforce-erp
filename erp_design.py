"""Visual theme for the authenticated ERP workspace."""

WORKSPACE_STYLE = """
<style>
body:has(.erp-workspace-theme) [data-testid="stAppViewContainer"] {
  background: radial-gradient(ellipse at 85% 0%, #18304755, transparent 42%), #09121e !important;
}
body:has(.erp-workspace-theme) [data-testid="stMain"] .block-container {
  box-sizing: border-box !important;
  width: 100% !important;
  max-width: 1600px !important;
  min-width: 0 !important;
  margin-inline: auto !important;
  padding: 4.75rem clamp(1rem, 2vw, 2rem) 3.5rem !important;
}
body:has(.erp-workspace-theme) header[data-testid="stHeader"] {
  height: 3.5rem !important;
  min-height: 3.5rem !important;
  background: #09121ef5 !important;
  border-bottom: 1px solid #22364c !important;
}
body:has(.erp-workspace-theme) [data-testid="stMain"] {
  min-width: 0 !important;
}
body:has(.erp-workspace-theme) [data-testid="stMain"] [data-testid="stColumn"],
body:has(.erp-workspace-theme) [data-testid="stMain"] [data-testid="stVerticalBlock"],
body:has(.erp-workspace-theme) [data-testid="stMain"] [data-testid="stElementContainer"],
body:has(.erp-workspace-theme) [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
  min-width: 0 !important;
  box-sizing: border-box !important;
}
body:has(.erp-workspace-theme) [data-testid="stMain"] [data-testid="stElementContainer"] {
  max-width: 100% !important;
}
body:has(.erp-workspace-theme) .v83-live-strip,
body:has(.erp-workspace-theme) .v10-panel-title {
  flex-wrap: wrap !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
body:has(.erp-workspace-theme) [data-testid="stTabs"] [role="tablist"] {
  overflow-x: auto !important;
  max-width: 100% !important;
}
body:has(.erp-workspace-theme) .v8-compact-table {
  max-width: 100% !important;
  overflow-x: auto !important;
}
body:has(.erp-workspace-theme) .stButton button p {
  white-space: normal !important;
  overflow-wrap: anywhere;
}
body:has(.erp-workspace-theme) [data-testid="stSidebar"] {
  width: 252px !important;
  min-width: 252px !important;
  max-width: min(252px, 85vw) !important;
  background: linear-gradient(180deg,#0d1c2d,#0b1624) !important;
  border-right: 1px solid #22364c !important;
}
body:has(.erp-workspace-theme) [data-testid="stSidebar"] > div {
  width: 100% !important;
  min-width: 0 !important;
  box-sizing: border-box !important;
}
body:has(.erp-workspace-theme) [data-testid="stSidebarContent"] {
  overflow-x: hidden !important;
  overflow-y: auto !important;
}
body:has(.erp-workspace-theme) [data-testid="stSidebarUserContent"] {
  padding: 1rem .85rem 2rem !important;
}
body:has(.erp-workspace-theme) .v10-sidebrand {
  display: grid !important;
  grid-template-columns: 38px minmax(0,1fr) !important;
  gap: 9px !important;
  align-items: center !important;
  padding: 11px 9px !important;
  margin: 0 0 10px !important;
}
body:has(.erp-workspace-theme) .v10-sidebrand img {
  width: 36px !important;
  height: 46px !important;
}
body:has(.erp-workspace-theme) .v10-sidebrand-copy {
  min-width: 0 !important;
}
body:has(.erp-workspace-theme) .v10-sidebrand-copy b,
body:has(.erp-workspace-theme) .v10-sidebrand-copy strong {
  font-size: 10px !important;
  line-height: 1.35 !important;
  white-space: normal !important;
  overflow-wrap: anywhere;
}
body:has(.erp-workspace-theme) .v10-sidebrand-copy small {
  font-size: 8px !important;
  margin-top: 5px !important;
}
body:has(.erp-workspace-theme) [data-testid="stSidebar"] [role="radiogroup"] {
  gap: .32rem !important;
}
body:has(.erp-workspace-theme) [data-testid="stSidebar"] [role="radiogroup"] label {
  padding: .4rem .55rem !important;
  min-height: 34px !important;
  border-radius: 9px !important;
  transition: background .15s ease;
}
body:has(.erp-workspace-theme) [data-testid="stSidebar"] [role="radiogroup"] label:hover {
  background: #19314a !important;
}
body:has(.erp-workspace-theme) [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background: linear-gradient(90deg,#214465,#182d43) !important;
  box-shadow: inset 3px 0 #6ccecf;
}
body:has(.erp-workspace-theme) h1, body:has(.erp-workspace-theme) h2,
body:has(.erp-workspace-theme) h3 { color: #edf4fa !important; letter-spacing: -.025em !important; }
body:has(.erp-workspace-theme) [data-testid="stVerticalBlockBorderWrapper"] > div {
  border-radius: 15px !important;
  border-color: #263a50 !important;
}
body:has(.erp-workspace-theme) [data-testid="stDataFrame"] {
  border: 1px solid #293d52;
  border-radius: 10px;
  overflow: hidden;
}
body:has(.erp-workspace-theme) [data-testid="stMetric"] {
  box-sizing: border-box;
  min-width: 0;
  max-width: 100%;
  background: linear-gradient(145deg,#16273b,#111f30);
  border: 1px solid #2b3f55;
  border-radius: 12px;
  padding: 1rem 1.15rem;
}
body:has(.erp-workspace-theme) [data-testid="stMetricValue"] {
  color: #eef5fc !important;
  font-variant-numeric: tabular-nums;
}
body:has(.erp-workspace-theme) .v10-hero {
  border-radius: 18px !important;
  border: 1px solid #46627c88 !important;
  min-height: 205px !important;
  box-shadow: 0 16px 36px #00000029 !important;
}
body:has(.erp-workspace-theme) .v10-hero h2 {
  font-size: clamp(1.8rem,3vw,2.65rem) !important;
  line-height: 1.16 !important;
  letter-spacing: -.04em !important;
  margin-bottom: .65rem !important;
}
body:has(.erp-workspace-theme) .v10-hero-kicker {
  color: #a8c9df !important;
  letter-spacing: .12em !important;
  font-size: .69rem !important;
}
body:has(.erp-workspace-theme) .v10-hero-left p { color: #d4e1ed !important; }
body:has(.erp-workspace-theme) .v10-hero-pills {
  display: flex !important; flex-wrap: wrap !important; gap: .45rem !important;
}
body:has(.erp-workspace-theme) .v10-hero-pills > span {
  background: #081a2aab !important; border: 1px solid #708da44d !important;
  color: #e2edf5 !important; border-radius: 6px !important; padding: .4rem .6rem !important;
}
body:has(.erp-workspace-theme) .v10-clock-card {
  background: #0b1c2bbd !important;
  border: 1px solid #61809766 !important;
  border-radius: 12px !important;
  backdrop-filter: blur(16px);
}
body:has(.erp-workspace-theme) .v10-kpi {
  box-sizing: border-box !important;
  width: 100% !important;
  background: linear-gradient(150deg,#192b40,#102033) !important;
  border: 1px solid #304760 !important;
  border-radius: 12px !important;
  box-shadow: 0 5px 15px #0000001a !important;
  min-height: 108px !important;
  padding: 15px !important;
}
body:has(.erp-workspace-theme) .v10-kpi small {
  color: #c3d1df !important; font-size: 11px !important; font-weight: 600 !important;
}
body:has(.erp-workspace-theme) .v10-kpi b {
  color: #f1f6fc !important; font-size: clamp(1.3rem,1.85vw,1.9rem) !important;
  letter-spacing: -.025em !important; font-variant-numeric: tabular-nums;
}
body:has(.erp-workspace-theme) .v10-kpi span { color: #a1b6cb !important; font-size: 10px !important; }
body:has(.erp-workspace-theme) .v10-kpi-icon {
  border-radius: 9px !important; box-shadow: none !important;
}
body:has(.erp-workspace-theme) .v10-panel-title {
  padding-bottom: .85rem !important; margin-bottom: .8rem !important;
  border-bottom: 1px solid #2a4057 !important;
}
body:has(.erp-workspace-theme) .v10-panel-title > span {
  color: #dce8f3 !important; font-size: 12px !important; letter-spacing: .045em !important;
}
body:has(.erp-workspace-theme) .v10-panel-title small {
  color: #9cb1c7 !important; font-size: 10px !important;
}
body:has(.erp-workspace-theme) .v10-product-line { color: #dce8f3 !important; }
body:has(.erp-workspace-theme) .v10-product-line b { font-size: 19px !important; }
body:has(.erp-workspace-theme) .v10-product-line span { color: #9cb1c7 !important; }
body:has(.erp-workspace-theme) .v10-alert-row,
body:has(.erp-workspace-theme) .v10-activity-row {
  padding: .8rem .25rem !important; border-bottom: 1px solid #24394f !important;
}
@media(max-width: 900px) {
  body:has(.erp-workspace-theme) [data-testid="stMain"] .block-container {
    padding: 4.5rem 1rem 3rem !important;
  }
  body:has(.erp-workspace-theme) [data-testid="stMain"] [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: .8rem !important;
  }
  body:has(.erp-workspace-theme) [data-testid="stMain"] [data-testid="stColumn"] {
    flex: 1 1 min(100%, 300px) !important;
    width: auto !important;
  }
  body:has(.erp-workspace-theme) .v10-hero { min-height: 225px !important; }
  body:has(.erp-workspace-theme) .v10-clock-card { display: none !important; }
}
@media(max-width: 600px) {
  body:has(.erp-workspace-theme) [data-testid="stMain"] [data-testid="stColumn"] {
    flex-basis: 100% !important;
    width: 100% !important;
  }
  body:has(.erp-workspace-theme) .v10-hero { padding: 18px !important; }
  body:has(.erp-workspace-theme) .v10-hero-left { max-width: 100% !important; }
  body:has(.erp-workspace-theme) .v10-hero-pills > span { white-space: normal !important; }
}
@media(prefers-reduced-motion: reduce) {
  body:has(.erp-workspace-theme) [data-testid="stSidebar"] label { transition: none !important; }
}
</style>
"""
