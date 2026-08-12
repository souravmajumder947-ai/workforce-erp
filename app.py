
import psycopg2
import pandas as pd
import streamlit as st


from datetime import date




st.set_page_config(
    page_title="HR & Production Cost Dashboard",
    page_icon="🏭",
    layout="wide",
)

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #253249;
    padding: 14px;
    border-radius: 12px;
}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {color: white;}
</style>
""", unsafe_allow_html=True)


def get_conn():
    return get_pg_conn()


def get_pg_conn():
    return psycopg2.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        dbname=st.secrets["postgres"]["dbname"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
    )
def test_postgres_connection():
    conn = get_pg_conn()
    cur = conn.cursor()
    cur.execute("SELECT current_database();")
    database_name = cur.fetchone()[0]
    cur.close()
    conn.close()
    return database_name

def init_db():
    with get_conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS departments(
            department TEXT PRIMARY KEY,
            active TEXT NOT NULL DEFAULT 'Yes'
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS employees(
            employee_id TEXT PRIMARY KEY,
            employee_name TEXT NOT NULL,
            department TEXT NOT NULL,
            designation TEXT NOT NULL,
            employee_type TEXT NOT NULL,
            shift TEXT NOT NULL,
            skill_level TEXT,
            monthly_salary REAL NOT NULL DEFAULT 0,
            ot_rate REAL NOT NULL DEFAULT 0,
            working_days INTEGER NOT NULL DEFAULT 26,
            joining_date TEXT,
            mobile_number TEXT,
            email TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            remarks TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS machines(
            machine TEXT PRIMARY KEY,
            department TEXT NOT NULL,
            standard_manpower INTEGER NOT NULL,
            target_ton REAL NOT NULL
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT NOT NULL,
            shift TEXT NOT NULL,
            employee_id TEXT NOT NULL,
            status TEXT NOT NULL,
            ot_hours REAL NOT NULL DEFAULT 0,
            UNIQUE(work_date, shift, employee_id)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS manpower_allocation(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT NOT NULL,
            shift TEXT NOT NULL,
            machine TEXT NOT NULL,
            employee_id TEXT NOT NULL,
            role TEXT NOT NULL,
            UNIQUE(work_date, shift, machine, employee_id)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS production(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT NOT NULL,
            shift TEXT NOT NULL,
            machine TEXT NOT NULL,
            production_ton REAL NOT NULL DEFAULT 0,
            target_ton REAL NOT NULL DEFAULT 0,
            waste_ton REAL NOT NULL DEFAULT 0,
            breakdown_hours REAL NOT NULL DEFAULT 0,
            UNIQUE(work_date, shift, machine)
        )
        """)

        existing_cols = {
            row[1] for row in c.execute("PRAGMA table_info(employees)").fetchall()
        }
        migrations = {
            "skill_level": "TEXT",
            "joining_date": "TEXT",
            "mobile_number": "TEXT",
            "email": "TEXT",
            "status": "TEXT NOT NULL DEFAULT 'Active'",
            "remarks": "TEXT",
        }
        for col, definition in migrations.items():
            if col not in existing_cols:
                c.execute(f"ALTER TABLE employees ADD COLUMN {col} {definition}")

        if c.execute("SELECT COUNT(*) FROM departments").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO departments(department,active) VALUES (?,?)",
                [
                    ("Corrugation","Yes"), ("Printing","Yes"), ("Conversion","Yes"),
                    ("Finishing","Yes"), ("Dispatch","Yes"), ("HR","Yes"),
                    ("Maintenance","Yes"), ("Stores","Yes"), ("ERP / IT","Yes"),
                    ("Accounts","Yes"), ("Quality","Yes"), ("Administration","Yes")
                ]
            )

        if c.execute("SELECT COUNT(*) FROM machines").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO machines(machine,department,standard_manpower,target_ton) VALUES (?,?,?,?)",
                [
                    ("Corrugation","Corrugation",18,50),
                    ("Topra 1228","Printing",17,48),
                    ("Topra 1632","Printing",10,20),
                    ("Flexo 2535","Printing",9,20),
                    ("Glue Folder","Finishing",10,22),
                    ("Stitching Machine 1","Finishing",12,25),
                    ("Stitching Machine 2","Finishing",10,20),
                    ("Stitching Machine 3","Finishing",10,20),
                    ("Stitching Machine 4","Finishing",12,25),
                    ("Stitching Machine 5","Finishing",14,25),
                ]
            )


def read_df(sql, params=()):
    pg_sql = sql.replace("?", "%s")

    conn = get_pg_conn()

    try:
        cur = conn.cursor()
        cur.execute(pg_sql, params)

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

        cur.close()

        return pd.DataFrame(rows, columns=columns)

    finally:
        conn.close()


def upsert(sql, params):
    pg_sql = sql.replace("?", "%s")

    conn = get_pg_conn()

    try:
        cur = conn.cursor()
        cur.execute(pg_sql, params)

        conn.commit()

        cur.close()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def normalize_text(value, default=""):
    if pd.isna(value):
        return default
    return str(value).strip()


def normalize_number(value, default=0.0):
    if pd.isna(value) or value == "":
        return default
    return float(value)


def normalize_int(value, default=26):
    if pd.isna(value) or value == "":
        return default
    return int(float(value))


def normalize_date(value):
    if pd.isna(value) or value == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def import_employee_excel(uploaded_file):
    try:
        excel = pd.ExcelFile(
            uploaded_file,
            engine="openpyxl"
        )
    
        sheet = (
            "Employee_Data"
            if "Employee_Data" in excel.sheet_names
            else excel.sheet_names[0]
        )

        df = pd.read_excel(
            uploaded_file,
            sheet_name=sheet,
            header=2,
            engine="openpyxl"
        )

    except Exception as exc:
        raise ValueError(
            f"Unable to read Excel file: {exc}"
        ) from exc

    required = [
        "Employee ID",
        "Employee Name",
        "Department",
        "Designation",
        "Employee Type",
        "Shift",
        "Monthly Salary",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    df = df.dropna(how="all").copy()
    if df.empty:
        raise ValueError("No employee rows were found.")

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    existing_ids = set(read_df("SELECT employee_id FROM employees")["employee_id"].astype(str))

    with get_pg_conn() as c:
        cur = c.cursor()
        for idx, row in df.iterrows():
            excel_row = idx + 4
            emp_id = normalize_text(row.get("Employee ID"))
            name = normalize_text(row.get("Employee Name"))
            department = normalize_text(row.get("Department"))
            designation = normalize_text(row.get("Designation"))

            if not emp_id and not name:
                skipped += 1
                continue

            if not emp_id or not name or not department or not designation:
                errors.append(f"Row {excel_row}: Employee ID, name, department and designation are required.")
                continue

            employee_type = normalize_text(row.get("Employee Type"), "Permanent")
            shift = normalize_text(row.get("Shift"), "General")
            skill = normalize_text(row.get("Skill Level"), "")
            monthly_salary = normalize_number(row.get("Monthly Salary"), 0)
            working_days = normalize_int(row.get("Working Days / Month"), 26)
            ot_rate = normalize_number(row.get("OT Rate / Hour"), 0)
            joining_date = normalize_date(row.get("Joining Date"))
            mobile = normalize_text(row.get("Mobile Number"), "")
            email = normalize_text(row.get("Email"), "")
            status = normalize_text(row.get("Status"), "Active")
            remarks = normalize_text(row.get("Remarks"), "")

            if working_days <= 0:
                errors.append(f"Row {excel_row}: Working days must be greater than zero.")
                continue
            if monthly_salary < 0 or ot_rate < 0:
                errors.append(f"Row {excel_row}: Salary and OT rate cannot be negative.")
                continue

            was_existing = emp_id in existing_ids

            cur.execute("""
                INSERT INTO employees(
                    employee_id, employee_name, department, designation,
                    employee_type, shift, skill_level, monthly_salary,
                    ot_rate, working_days, joining_date, mobile_number,
                    email, status, remarks
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(employee_id) DO UPDATE SET
                    employee_name=excluded.employee_name,
                    department=excluded.department,
                    designation=excluded.designation,
                    employee_type=excluded.employee_type,
                    shift=excluded.shift,
                    skill_level=excluded.skill_level,
                    monthly_salary=excluded.monthly_salary,
                    ot_rate=excluded.ot_rate,
                    working_days=excluded.working_days,
                    joining_date=excluded.joining_date,
                    mobile_number=excluded.mobile_number,
                    email=excluded.email,
                    status=excluded.status,
                    remarks=excluded.remarks
            """, (
                emp_id, name, department, designation, employee_type, shift,
                skill, monthly_salary, ot_rate, working_days, joining_date,
                mobile, email, status, remarks
            ))

            cur.execute("""
                INSERT INTO departments(department, active) VALUES (%s, 'Yes')
                ON CONFLICT(department) DO NOTHING
            """, (department,))

            if was_existing:
                updated += 1
            else:
                imported += 1
                existing_ids.add(emp_id)

    c.commit()
    cur.close()

    return {
        "total_rows": len(df),
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


def dashboard_data(report_date, selected_shift):
    date_text = report_date.isoformat()
    shift_filter = "" if selected_shift == "All" else " AND shift = ?"
    params = (date_text,) if selected_shift == "All" else (date_text, selected_shift)

    employees = read_df("SELECT * FROM employees WHERE status='Active'")
    attendance = read_df(
        f"SELECT * FROM attendance WHERE work_date = ?{shift_filter}", params
    )
    allocations = read_df(
        f"SELECT * FROM manpower_allocation WHERE work_date = ?{shift_filter}", params
    )
    production = read_df(
        f"SELECT * FROM production WHERE work_date = ?{shift_filter}", params
    )
    machines = read_df("SELECT * FROM machines ORDER BY machine")

    if attendance.empty:
        present_ids = set()
        absent_count = leave_count = 0
        ot_cost = attendance_cost = 0.0
    else:
        present = attendance[attendance["status"] == "Present"].copy()
        present_ids = set(present["employee_id"])
        absent_count = int((attendance["status"] == "Absent").sum())
        leave_count = int((attendance["status"] == "Leave").sum())

        cost_df = attendance.merge(
            employees[["employee_id","monthly_salary","ot_rate","working_days"]],
            on="employee_id", how="left"
        )
        cost_df["daily_cost"] = (
            cost_df["monthly_salary"] / cost_df["working_days"].replace(0, pd.NA)
        ).fillna(0)
        cost_df["attendance_cost"] = cost_df.apply(
            lambda r: r["daily_cost"] if r["status"] == "Present" else 0, axis=1
        )
        cost_df["ot_cost"] = cost_df["ot_hours"] * cost_df["ot_rate"]
        attendance_cost = float(cost_df["attendance_cost"].sum())
        ot_cost = float(cost_df["ot_cost"].sum())

    total_labour_cost = attendance_cost + ot_cost
    total_production = float(production["production_ton"].sum()) if not production.empty else 0.0
    total_target = float(production["target_ton"].sum()) if not production.empty else 0.0
    cost_per_ton = total_labour_cost / total_production if total_production else 0.0
    efficiency = total_production / total_target if total_target else 0.0

    if allocations.empty:
        alloc_summary = pd.DataFrame(columns=["machine","actual_manpower"])
    else:
        alloc_summary = allocations.groupby("machine", as_index=False).agg(
            actual_manpower=("employee_id","nunique")
        )

    prod_summary = production.groupby("machine", as_index=False).agg(
        production_ton=("production_ton","sum"),
        target_ton=("target_ton","sum"),
        waste_ton=("waste_ton","sum"),
        breakdown_hours=("breakdown_hours","sum"),
    ) if not production.empty else pd.DataFrame(
        columns=["machine","production_ton","target_ton","waste_ton","breakdown_hours"]
    )

    analysis = machines.merge(alloc_summary, on="machine", how="left").merge(
        prod_summary, on="machine", how="left", suffixes=("_master","_actual")
    ).fillna(0)

    multiplier = 2 if selected_shift == "All" else 1
    analysis["standard_manpower_display"] = analysis["standard_manpower"] * multiplier
    analysis["target_ton_display"] = analysis.apply(
        lambda r: r["target_ton_actual"] if r["target_ton_actual"] > 0
        else r["target_ton_master"] * multiplier, axis=1
    )
    analysis["manpower_gap"] = analysis["actual_manpower"] - analysis["standard_manpower_display"]
    analysis["efficiency"] = (
        analysis["production_ton"] / analysis["target_ton_display"].replace(0, pd.NA)
    ).fillna(0)

    def status(row):
        if row["production_ton"] == 0:
            return "No Production"
        if row["manpower_gap"] > 1:
            return "Overstaffed"
        if row["manpower_gap"] < -1:
            return "Understaffed"
        return "Optimal"

    analysis["status"] = analysis.apply(status, axis=1)
    analysis["recommendation"] = analysis.apply(
        lambda r: f"Reallocate {int(r['manpower_gap'])} people"
        if r["status"] == "Overstaffed"
        else (
            f"Add {abs(int(r['manpower_gap']))} people"
            if r["status"] == "Understaffed"
            else ("Check data/machine" if r["status"] == "No Production" else "Maintain")
        ), axis=1
    )

    return {
        "employees": employees,
        "attendance": attendance,
        "allocations": allocations,
        "production": production,
        "analysis": analysis,
        "present_count": len(present_ids),
        "absent_count": absent_count,
        "leave_count": leave_count,
        "attendance_cost": attendance_cost,
        "ot_cost": ot_cost,
        "total_labour_cost": total_labour_cost,
        "total_production": total_production,
        "cost_per_ton": cost_per_ton,
        "efficiency": efficiency,
    }


# init_db()   # Old SQLite database initialization disabled

st.title("HR & Production Cost Management System")
st.caption("Employee cost, attendance, manpower allocation, production and cost-per-ton analysis")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard", "Employee Master", "Attendance",
        "Manpower Allocation", "Production Entry",
        "Machine Master", "Reports",
    ],
)

if page == "Dashboard":
    c1, c2 = st.columns(2)
    report_date = c1.date_input("Report Date", value=date.today())
    selected_shift = c2.selectbox("Shift", ["All","A","B"])
    data = dashboard_data(report_date, selected_shift)

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Present", data["present_count"])
    k2.metric("Production", f"{data['total_production']:.2f} ton")
    k3.metric("Labour Cost", f"₹{data['total_labour_cost']:,.0f}")
    k4.metric("Cost / Ton", f"₹{data['cost_per_ton']:,.0f}")
    k5.metric("Efficiency", f"{data['efficiency']:.1%}")

    a,b,c,d = st.columns(4)
    a.metric("Absent", data["absent_count"])
    b.metric("On Leave", data["leave_count"])
    c.metric("Attendance Cost", f"₹{data['attendance_cost']:,.0f}")
    d.metric("OT Cost", f"₹{data['ot_cost']:,.0f}")

    show = data["analysis"][[
        "machine","department","standard_manpower_display","actual_manpower",
        "production_ton","target_ton_display","manpower_gap","efficiency",
        "status","recommendation"
    ]].copy()
    show.columns = [
        "Machine","Department","Standard MP","Actual MP","Production Ton",
        "Target Ton","MP Gap","Efficiency","Status","Recommendation"
    ]
    show["Efficiency"] = show["Efficiency"].map(lambda x: f"{x:.1%}")
    st.dataframe(show, width="stretch", hide_index=True)

elif page == "Employee Master":
    st.subheader("Employee Master")

    st.markdown("### Import Employees from Excel")
    uploaded_file = st.file_uploader(
        "Upload the completed Employee Master template",
        type=["xlsx", "xls"],
        help="Use the Employee_Data sheet and keep the original column names."
    )

    if uploaded_file is not None:
        if st.button("Import / Update Employees", type="primary", width="stretch"):
            try:
                result = import_employee_excel(uploaded_file)
                st.success(
                    f"Import completed — New: {result['imported']}, "
                    f"Updated: {result['updated']}, Skipped: {result['skipped']}."
                )
                if result["errors"]:
                    st.warning(f"{len(result['errors'])} row(s) had errors.")
                    with st.expander("View import errors"):
                        for error in result["errors"][:100]:
                            st.write(error)
                else:
                    st.balloons()
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.divider()
    st.markdown("### Add or Update One Employee")

    departments = read_df(
        "SELECT department FROM departments WHERE active='Yes' ORDER BY department"
    )["department"].tolist()

    with st.form("employee_form"):
        c1,c2,c3,c4 = st.columns(4)
        employee_id = c1.text_input("Employee ID")
        employee_name = c2.text_input("Employee Name")
        department = c3.selectbox("Department", departments)
        designation = c4.text_input("Designation")

        c1,c2,c3,c4 = st.columns(4)
        employee_type = c1.selectbox("Employee Type", ["Permanent","Contract"])
        shift = c2.selectbox("Default Shift", ["A","B","General"])
        skill_level = c3.selectbox("Skill Level", ["Skilled","Semi-skilled","Unskilled"])
        monthly_salary = c4.number_input("Monthly Salary", min_value=0.0, step=500.0)

        c1,c2,c3,c4 = st.columns(4)
        ot_rate = c1.number_input("OT Rate / Hour", min_value=0.0, step=10.0)
        working_days = c2.number_input("Working Days / Month", min_value=1, max_value=31, value=26)
        joining_date = c3.date_input("Joining Date", value=date.today())
        status = c4.selectbox("Status", ["Active","Inactive"])

        c1,c2 = st.columns(2)
        mobile = c1.text_input("Mobile Number")
        email = c2.text_input("Email")
        remarks = st.text_area("Remarks")

        save = st.form_submit_button("Save Employee", width="stretch")

    if save:
        if not employee_id.strip() or not employee_name.strip() or not designation.strip():
            st.error("Employee ID, employee name and designation are required.")
        else:
            upsert("""
            INSERT INTO employees(
                employee_id,employee_name,department,designation,employee_type,
                shift,skill_level,monthly_salary,ot_rate,working_days,
                joining_date,mobile_number,email,status,remarks
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(employee_id) DO UPDATE SET
                employee_name=excluded.employee_name,
                department=excluded.department,
                designation=excluded.designation,
                employee_type=excluded.employee_type,
                shift=excluded.shift,
                skill_level=excluded.skill_level,
                monthly_salary=excluded.monthly_salary,
                ot_rate=excluded.ot_rate,
                working_days=excluded.working_days,
                joining_date=excluded.joining_date,
                mobile_number=excluded.mobile_number,
                email=excluded.email,
                status=excluded.status,
                remarks=excluded.remarks
            """, (
                employee_id.strip(), employee_name.strip(), department,
                designation.strip(), employee_type, shift, skill_level,
                float(monthly_salary), float(ot_rate), int(working_days),
                joining_date.isoformat(), mobile.strip(), email.strip(),
                status, remarks.strip()
            ))
            st.success("Employee saved.")
            st.rerun()

    employees = read_df("SELECT * FROM employees ORDER BY employee_name")
    if not employees.empty:
        employees["daily_cost"] = (
            employees["monthly_salary"] / employees["working_days"].replace(0, pd.NA)
        ).fillna(0)
        search = st.text_input("Search employee")
        if search:
            mask = employees.astype(str).apply(
                lambda col: col.str.contains(search, case=False, na=False)
            ).any(axis=1)
            employees = employees[mask]
    st.dataframe(employees, width="stretch", hide_index=True)

elif page == "Attendance":
    st.subheader("Daily Attendance & Overtime")

    c1, c2 = st.columns(2)
    work_date = c1.date_input("Attendance Date", value=date.today())
    shift = c2.selectbox("Shift", ["A", "B", "General"])

    employees = read_df("""
        SELECT employee_id, employee_name, department
        FROM employees
        WHERE status = 'Active'
        ORDER BY department, employee_name
    """)

    if employees.empty:
        st.info("Please add or import employees first.")

    else:
        existing = read_df("""
            SELECT employee_id, status, ot_hours
            FROM attendance
            WHERE work_date = ? AND shift = ?
        """, (work_date.isoformat(), shift))

        attendance_df = employees.merge(
            existing,
            on="employee_id",
            how="left"
        )

        attendance_df["status"] = attendance_df["status"].fillna("Not Marked")
        attendance_df["ot_hours"] = attendance_df["ot_hours"].fillna(0.0)

        st.caption(
            f"Employees: {len(attendance_df)} | "
            f"Date: {work_date.strftime('%d-%m-%Y')} | Shift: {shift}"
        )

        edited_attendance = st.data_editor(
            attendance_df,
            hide_index=True,
            width="stretch",
            column_config={
                "employee_id": st.column_config.TextColumn(
                    "Employee ID",
                    disabled=True
                ),
                "employee_name": st.column_config.TextColumn(
                    "Employee Name",
                    disabled=True
                ),
                "department": st.column_config.TextColumn(
                    "Department",
                    disabled=True
                ),
                "status": st.column_config.SelectboxColumn(
                    "Attendance Status",
                    options=[
                        "Not Marked",
                        "Present",
                        "Absent",
                        "Leave",
                        "Holiday"
                    ],
                    required=True
                ),
                "ot_hours": st.column_config.NumberColumn(
                    "OT Hours",
                    min_value=0.0,
                    max_value=12.0,
                    step=0.5
                )
            }
        )

        if st.button(
            "Save Attendance",
            type="primary",
            width="stretch"
        ):
            rows_saved = 0

            with get_pg_conn() as c:
                cur = c.cursor()
                for _, row in edited_attendance.iterrows():

                    if row["status"] == "Not Marked":
                        continue

                    ot_hours = float(row["ot_hours"])

                    if row["status"] != "Present":
                        ot_hours = 0.0

                    cur.execute("""
                        INSERT INTO attendance(
                            work_date,
                            shift,
                            employee_id,
                            status,
                            ot_hours
                        )
                        VALUES (%s, %s, %s, %s, %s)

                        ON CONFLICT(work_date, shift, employee_id)
                        DO UPDATE SET
                            status = excluded.status,
                            ot_hours = excluded.ot_hours
                    """, (
                        work_date.isoformat(),
                        shift,
                        str(row["employee_id"]),
                        row["status"],
                        ot_hours
                    ))

                    rows_saved += 1

                c.commit()
                cur.close()

            st.success(
                f"Attendance saved successfully for {rows_saved} employees."
            )
            st.rerun()

        st.divider()

        present_count = int(
            (edited_attendance["status"] == "Present").sum()
        )

        absent_count = int(
            (edited_attendance["status"] == "Absent").sum()
        )

        leave_count = int(
            (edited_attendance["status"] == "Leave").sum()
        )

        total_ot = pd.to_numeric(
    edited_attendance.loc[
        edited_attendance["status"] == "Present",
        "ot_hours"
    ],
    errors="coerce"
).fillna(0).sum()

        m1, m2, m3, m4 = st.columns(4)

        m1.metric("Present", present_count)
        m2.metric("Absent", absent_count)
        m3.metric("Leave", leave_count)
        m4.metric("Total OT Hours", f"{total_ot:.1f}")

elif page == "Manpower Allocation":
    st.subheader("Employee-to-Machine Allocation")
    employees = read_df(
        "SELECT employee_id,employee_name FROM employees WHERE status='Active' ORDER BY employee_name"
    )
    machines = read_df("SELECT machine FROM machines ORDER BY machine")["machine"].tolist()
    if employees.empty:
        st.info("Add or import employees first.")
    else:
        employee_options = employees["employee_id"] + " - " + employees["employee_name"]
        with st.form("allocation_form"):
            c1,c2,c3,c4,c5 = st.columns(5)
            work_date = c1.date_input("Date", value=date.today())
            shift = c2.selectbox("Shift", ["A","B"])
            machine = c3.selectbox("Machine", machines)
            selected_employee = c4.selectbox("Employee", employee_options)
            role = c5.selectbox("Role", ["Operator","Helper","Supervisor"])
            save = st.form_submit_button("Save Allocation", width="stretch")
        if save:
            employee_id = selected_employee.split(" - ")[0]
            upsert("""
            INSERT INTO manpower_allocation(work_date,shift,machine,employee_id,role)
            VALUES (?,?,?,?,?)
            ON CONFLICT(work_date,shift,machine,employee_id) DO UPDATE SET
                role=excluded.role
            """, (work_date.isoformat(),shift,machine,employee_id,role))
            st.success("Allocation saved.")
            st.rerun()

       
        st.divider()
        st.subheader("Saved Allocations")

        saved_allocations = read_df(
        """
        SELECT
            ma.work_date,
            ma.shift,
            ma.machine,
            ma.employee_id,
            e.employee_name,
            ma.role
        FROM manpower_allocation ma
        LEFT JOIN employees e
            ON e.employee_id = ma.employee_id
        WHERE ma.work_date = ? AND ma.shift = ?
        ORDER BY ma.machine, e.employee_name
        """,
        (work_date.isoformat(), shift)
    )

    if saved_allocations.empty:
        st.info("No manpower allocations saved for this date and shift.")
    else:
        saved_allocations.columns = [
            "Date",
            "Shift",
            "Machine",
            "Employee ID",
            "Employee Name",
            "Role",
        ]

        st.dataframe(
            saved_allocations,
            use_container_width=True,
            hide_index=True
        )

    if not saved_allocations.empty:
        st.subheader("Manage Allocation")

        allocation_options = (
            saved_allocations["Employee ID"].astype(str)
            + " - "
            + saved_allocations["Employee Name"].astype(str)
            + " - "
            + saved_allocations["Machine"].astype(str)
        )

        selected_allocation = st.selectbox(
            "Select Allocation",
            allocation_options.tolist()
        )

        selected_index = allocation_options[
            allocation_options == selected_allocation
        ].index[0]

        selected_row = saved_allocations.loc[selected_index]

        c1, c2 = st.columns(2)

        new_role = c1.selectbox(
            "Update Role",
            ["Operator", "Helper", "Supervisor"],
            index=["Operator", "Helper", "Supervisor"].index(
                selected_row["Role"]
            )
            if selected_row["Role"] in ["Operator", "Helper", "Supervisor"]
            else 0
        )

        if c1.button("Update Allocation"):
            upsert(
                """
                UPDATE manpower_allocation
                SET role = ?
                WHERE work_date = ?
                  AND shift = ?
                  AND machine = ?
                  AND employee_id = ?
                """,
                (
                    new_role,
                    str(selected_row["Date"]),
                    selected_row["Shift"],
                    selected_row["Machine"],
                    str(selected_row["Employee ID"]),
                )
            )
            st.success("Allocation updated.")
            st.rerun()

        if c2.button("Delete Allocation"):
            upsert(
                """
                DELETE FROM manpower_allocation
                WHERE work_date = ?
                  AND shift = ?
                  AND machine = ?
                  AND employee_id = ?
                """,
                (
                    str(selected_row["Date"]),
                    selected_row["Shift"],
                    selected_row["Machine"],
                    str(selected_row["Employee ID"]),
                )
            )
            st.success("Allocation deleted.")
            st.rerun()       

elif page == "Production Entry":
    st.subheader("Production Entry")
    machine_df = read_df("SELECT machine,target_ton FROM machines ORDER BY machine")
    machines = machine_df["machine"].tolist()
    with st.form("production_form"):
        c1,c2,c3 = st.columns(3)
        work_date = c1.date_input("Date", value=date.today())
        shift = c2.selectbox("Shift", ["A","B"])
        machine = c3.selectbox("Machine", machines)
        default_target = float(
            machine_df.loc[machine_df["machine"] == machine, "target_ton"].iloc[0]
        )
        c1,c2,c3,c4 = st.columns(4)
        production_ton = c1.number_input("Production Ton", min_value=0.0, step=0.1)
        target_ton = c2.number_input("Target Ton", min_value=0.0, value=default_target, step=0.1)
        waste_ton = c3.number_input("Waste Ton", min_value=0.0, step=0.1)
        breakdown_hours = c4.number_input("Breakdown Hours", min_value=0.0, max_value=24.0, step=0.5)
        save = st.form_submit_button("Save Production", width="stretch")
    if save:
        upsert("""
        INSERT INTO production(work_date,shift,machine,production_ton,target_ton,waste_ton,breakdown_hours)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(work_date,shift,machine) DO UPDATE SET
            production_ton=excluded.production_ton,
            target_ton=excluded.target_ton,
            waste_ton=excluded.waste_ton,
            breakdown_hours=excluded.breakdown_hours
        """, (
            work_date.isoformat(),shift,machine,float(production_ton),
            float(target_ton),float(waste_ton),float(breakdown_hours)
        ))
        st.success("Production saved.")
        st.rerun()

elif page == "Machine Master":
    st.subheader("Machine Master")
    machines = read_df("SELECT * FROM machines ORDER BY machine")
    edited = st.data_editor(machines, width="stretch", hide_index=True, num_rows="dynamic")
    if st.button("Save Machine Master", width="stretch"):
        clean = edited.dropna(how="all").copy()
        clean["machine"] = clean["machine"].fillna("").astype(str).str.strip()
        clean["department"] = clean["department"].fillna("").astype(str).str.strip()
        clean = clean[clean["machine"] != ""].copy()
        if clean.empty:
            st.error("At least one machine is required.")
        elif clean["machine"].duplicated().any():
            st.error("Duplicate machine names are not allowed.")
        elif (clean["department"] == "").any():
            st.error("Department cannot be blank.")
        else:
            clean["standard_manpower"] = pd.to_numeric(clean["standard_manpower"], errors="coerce")
            clean["target_ton"] = pd.to_numeric(clean["target_ton"], errors="coerce")
            if clean[["standard_manpower","target_ton"]].isna().any().any():
                st.error("Standard manpower and target ton must be valid numbers.")
            else:
                rows = list(
                    clean[["machine","department","standard_manpower","target_ton"]]
                    .itertuples(index=False, name=None)
                )
                with get_pg_conn() as c:
                    cur = c.cursor()

                    cur.execute("DELETE FROM machines")

                    cur.executemany(
                        """
                        INSERT INTO machines(machine, department, standard_manpower, target_ton)
                        VALUES (%s, %s, %s, %s)
                        """,
                        [(m, d, int(mp), float(t)) for m, d, mp, t in rows]
                    )

                    c.commit()
                    cur.close()

                st.success("Machine Master saved.")
                st.rerun()

else:
    st.subheader("Reports")
    tabs = st.tabs(["Employees","Attendance","Allocation","Production"])
    reports = [
        ("employees.csv", read_df("SELECT * FROM employees")),
        ("attendance.csv", read_df("SELECT * FROM attendance")),
        ("allocation.csv", read_df("SELECT * FROM manpower_allocation")),
        ("production.csv", read_df("SELECT * FROM production")),
    ]
    for tab,(name,df) in zip(tabs,reports):
        with tab:
            st.dataframe(df, width="stretch", hide_index=True)
            st.download_button(
                f"Download {name}",
                df.to_csv(index=False).encode("utf-8"),
                file_name=name,
                mime="text/csv"
            )


try:
    pg_database = test_postgres_connection()
    st.success(f"PostgreSQL connected successfully: {pg_database}")
except Exception as e:
    st.error(f"PostgreSQL connection failed: {e}")
