"""Separate entry tasks from management review in the sidebar."""
import streamlit as st


MODE_LABELS = {
    "MD view": {"Home", "Employee 360", "Cost & Attrition"},
    "HR entries": {"HR workspace", "Attendance", "HR Review", "Employee records",
                   "Salary and statutory details", "Attendance and leave entry", "Payroll",
                   "Joining and leaving", "Employee 360 and letters"},
    "Operations": {"Production"},
    "Settings": {"Settings"},
}


WORKSPACE_NAMES = {
    "MD view": "MD Dashboard & Reports",
    "HR entries": "HR Data Entry",
    "Operations": "Production & Manpower",
    "Settings": "ERP Settings",
}

PAGE_NAMES = {
    "Home": "MD Dashboard",
    "Employee 360": "Employee Profiles",
    "Cost & Attrition": "Labour Cost & Attrition",
    "HR workspace": "HR Dashboard & Tasks",
    "Attendance": "Upload Attendance",
    "HR Review": "Resolve Attendance Issues",
    "Employee records": "Employee Master List",
    "Salary and statutory details": "Salary, PF & ESIC",
    "Attendance and leave entry": "Enter Attendance or Leave",
    "Payroll": "Run & Review Payroll",
    "Joining and leaving": "Joining & Exit Dates",
    "Employee 360 and letters": "Employee Profiles & Letters",
    "Production": "Enter Production & Manpower",
    "Settings": "Masters & ERP Settings",
}


def mode_routes(routes):
    return {
        mode: {label: target for label, target in routes.items() if label in labels}
        for mode, labels in MODE_LABELS.items()
        if any(label in routes for label in labels)
    }


def render_workspace_navigation(routes, role):
    modes = mode_routes(routes)
    current = st.session_state.get("simple_navigation")
    current_mode = next((mode for mode, group in modes.items() if current in group), None)
    if current_mode:
        st.session_state["workspace_menu"] = current_mode
    elif st.session_state.get("workspace_menu") not in modes:
        st.session_state["workspace_menu"] = "HR entries" if role == "HR" and "HR entries" in modes else next(iter(modes))

    def change_mode():
        group = modes[st.session_state["workspace_menu"]]
        st.session_state["simple_navigation"] = next(iter(group))

    st.sidebar.selectbox(
        "Switch workspace", list(modes), key="workspace_menu", on_change=change_mode,
        format_func=WORKSPACE_NAMES.__getitem__,
        help="Choose the kind of work you want to do. The pages below change with the workspace.",
    )
    mode = st.session_state["workspace_menu"]
    st.sidebar.markdown(
        '<div class="v5-sidebar-label">' +
        {"MD view": "MANAGEMENT REVIEW", "HR entries": "HR DATA ENTRY",
         "Operations": "PRODUCTION ENTRY", "Settings": "CONFIGURATION"}[mode] + "</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.caption({
        "MD view": "Overview, employee insights and reports",
        "HR entries": "Create, upload and update HR records",
        "Operations": "Production and manpower entries",
        "Settings": "Masters, access and configuration",
    }[mode])
    group = modes[mode]
    if st.session_state.get("simple_navigation") not in group:
        st.session_state["simple_navigation"] = next(iter(group))
    selected = st.sidebar.radio(
        "Pages in this workspace", list(group), key="simple_navigation",
        format_func=PAGE_NAMES.__getitem__, label_visibility="collapsed",
    )
    return selected


WORKSPACE_BUTTON_STYLE = """
<style>
[data-testid="stSidebar"] .st-key-simple_navigation [role="radiogroup"] > label {
    width: 100%;
    min-height: 40px;
}
body [data-testid="stSidebar"] .st-key-simple_navigation label p {
    font-size: 0.875rem !important;
    line-height: 1.35 !important;
    white-space: normal !important;
}

body .st-key-hr_entry_tasks .stButton[data-testid="stButton"] > button {
    background: linear-gradient(115deg,#143d39,#16302f) !important;
    border: 1px solid #448d7e !important;
    border-radius: 10px !important;
    color: #e0fff2 !important;
    min-height: 46px !important;
    box-shadow: inset 3px 0 #70c7a5 !important;
}
body .st-key-hr_entry_tasks .stButton[data-testid="stButton"] > button p {
    color: #e0fff2 !important;
    font-weight: 700 !important;
}
body .st-key-hr_entry_tasks .stButton[data-testid="stButton"] > button:hover {
    background: #205548 !important;
    border-color: #8ad9ba !important;
}
body .st-key-hr_entry_tasks .stButton[data-testid="stButton"] > button:focus-visible {
    outline: 3px solid #a6efcf;
    outline-offset: 2px;
}
body:has(.md-review-workspace) [data-testid="stSidebar"] .st-key-simple_navigation label:has(input:checked) {
    background: #343046 !important;
    box-shadow: inset 3px 0 #c7afe8 !important;
}
body:has(.hr-entry-workspace) [data-testid="stSidebar"] .st-key-simple_navigation label:has(input:checked) {
    background: #173d35 !important;
    box-shadow: inset 3px 0 #70c7a5 !important;
}
</style>
"""
