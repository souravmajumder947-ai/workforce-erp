from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

# ------------------------------------------------------------------
# 1) Add authoritative Employee Master XLSX helpers.
# ------------------------------------------------------------------
helper_marker = '''\n\n# ============================================================\n# BUSINESS RULES / ACCESS / REPORT HELPERS\n# ============================================================\n'''
if helper_marker not in text:
    raise SystemExit('business rules helper marker not found')

helpers = r'''

# ============================================================
# AUTHORITATIVE EMPLOYEE MASTER XLSX SYNC
# Latest HR rule: the supplied Employee_Data workbook is the source of truth
# for employee identity/employment fields and department names. No legacy
# department auto-mapping is applied here.
# ============================================================
def _authoritative_employee_id(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            number = float(value)
            if number.is_integer():
                return str(int(number))
        except Exception:
            pass
    raw = str(value).strip()
    if raw.endswith('.0') and raw[:-2].isdigit():
        return raw[:-2]
    return raw


def _authoritative_location_division(value):
    raw = _clean_text(value).upper()
    compact = ''.join(ch for ch in raw if ch.isalnum())
    if compact in {'GNOIDA','GREATERNOIDA','GREATERNOIDAPLANT','GNP','NOIDAPLANT'}:
        return 'Greater Noida Plant'
    if compact in {'HOD2','D2','D2NOIDA','D2SEC63','D63','D63HEADOFFICE','HEADOFFICE'}:
        return 'D-63 Head Office'
    if 'DHAULANA' in compact:
        return 'Dhaulana Glass Plant'
    if raw in DIVISIONS:
        return raw
    return ''


def _authoritative_bool(value, default=False):
    raw = _clean_text(value).strip().upper()
    if raw in {'YES','Y','TRUE','1','ACTIVE'}:
        return True
    if raw in {'NO','N','FALSE','0','INACTIVE'}:
        return False
    return bool(default)


def read_authoritative_employee_master_excel(uploaded_file):
    try:
        uploaded_file.seek(0)
        excel = pd.ExcelFile(uploaded_file, engine='openpyxl')
        sheet = 'Employee_Data' if 'Employee_Data' in excel.sheet_names else excel.sheet_names[0]
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, sheet_name=sheet, header=2, engine='openpyxl')
    except Exception as exc:
        raise ValueError(f'Unable to read Employee Master workbook: {exc}') from exc

    df.columns = [str(c).strip() for c in df.columns]
    required = [
        'Employee ID','Employee Name','Department','Designation','Employee Type',
        'Shift','Skill Level','Monthly Salary','Working Days / Month','OT Rate / Hour',
        'Joining Date','Status','Remarks','LOCATION','OT APPICABLE'
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError('Missing required column(s): ' + ', '.join(missing))

    work = df.copy()
    work['__employee_id'] = work['Employee ID'].apply(_authoritative_employee_id)
    work = work[work['__employee_id'].astype(str).str.fullmatch(r'\d+', na=False)].copy()
    if work.empty:
        raise ValueError('No valid employee rows were found in Employee_Data.')

    work['__division'] = work['LOCATION'].apply(_authoritative_location_division)
    work['__department'] = work['Department'].apply(_clean_text)
    work['__employee_name'] = work['Employee Name'].apply(_clean_text)
    work['__designation'] = work['Designation'].apply(_clean_text)

    errors = []
    duplicate_ids = sorted(
        work.loc[work['__employee_id'].duplicated(keep=False), '__employee_id'].astype(str).unique().tolist()
    )
    if duplicate_ids:
        errors.append('Duplicate Employee ID(s): ' + ', '.join(duplicate_ids[:30]))

    invalid_locations = work.loc[work['__division'].eq(''), 'LOCATION'].dropna().astype(str).str.strip().unique().tolist()
    if invalid_locations:
        errors.append('Unknown LOCATION value(s): ' + ', '.join(invalid_locations[:20]))

    for idx, row in work.iterrows():
        excel_row = int(idx) + 4
        if not row['__employee_name']:
            errors.append(f'Row {excel_row}: Employee Name is required.')
        if not row['__department']:
            errors.append(f'Row {excel_row}: Department is required.')
        if not row['__designation']:
            errors.append(f'Row {excel_row}: Designation is required.')
        if _num(row.get('Working Days / Month'), 0) <= 0:
            errors.append(f'Row {excel_row}: Working Days / Month must be greater than zero.')
        if _num(row.get('Monthly Salary'), 0) < 0:
            errors.append(f'Row {excel_row}: Monthly Salary cannot be negative.')
        if _num(row.get('OT Rate / Hour'), 0) < 0:
            errors.append(f'Row {excel_row}: OT Rate / Hour cannot be negative.')

    work = work.sort_values(['__division','__employee_id']).reset_index(drop=True)
    return work, errors


def preview_authoritative_employee_master_excel(uploaded_file):
    work, errors = read_authoritative_employee_master_excel(uploaded_file)
    location_summary = (
        work['__division'].value_counts().rename_axis('Division').reset_index(name='Employees')
    )
    department_summary = (
        work.groupby(['__division','__department'], as_index=False)['__employee_id']
        .nunique().rename(columns={'__division':'Division','__department':'Department','__employee_id':'Employees'})
        .sort_values(['Division','Department'])
    )
    preview_cols = [
        '__division','__employee_id','Employee Name','Department','Designation','Employee Type',
        'Shift','Skill Level','Monthly Salary','Working Days / Month','OT Rate / Hour',
        'Joining Date','Status','Remarks','LOCATION','OT APPICABLE'
    ]
    preview = work[[c for c in preview_cols if c in work.columns]].copy()
    preview = preview.rename(columns={'__division':'Division','__employee_id':'Employee ID'})
    return {
        'rows': len(work),
        'employees': int(work['__employee_id'].nunique()),
        'departments': int(work['__department'].nunique()),
        'divisions': int(work['__division'].nunique()),
        'errors': errors,
        'location_summary': location_summary,
        'department_summary': department_summary,
        'preview': preview,
    }


def sync_authoritative_employee_master_excel(uploaded_file, updated_by):
    work, errors = read_authoritative_employee_master_excel(uploaded_file)
    if errors:
        raise ValueError('\n'.join(errors[:100]))

    reference_ids = work['__employee_id'].astype(str).tolist()
    sync_divisions = sorted(work['__division'].astype(str).unique().tolist())
    exact_departments = sorted(work['__department'].astype(str).unique().tolist())

    conn = get_pg_conn()
    try:
        cur = conn.cursor()

        # Keep extra fields from the supplied master available for audit/search.
        cur.execute('ALTER TABLE employees ADD COLUMN IF NOT EXISTS aadhaar_number TEXT')
        cur.execute('ALTER TABLE employees ADD COLUMN IF NOT EXISTS location_code TEXT')
        cur.execute('ALTER TABLE employees ADD COLUMN IF NOT EXISTS ot_applicable BOOLEAN')

        # The supplied master is authoritative. Disable old automatic mappings so
        # Manual Area stays Manual Area, QA&QC stays QA&QC, ERP stays ERP, etc.
        cur.execute('UPDATE department_mappings SET active=FALSE')
        cur.execute("""
            INSERT INTO app_settings(setting_key, setting_value)
            VALUES ('authoritative_employee_master_mode', 'enabled')
            ON CONFLICT(setting_key) DO UPDATE SET setting_value='enabled'
        """)

        for dep in exact_departments:
            cur.execute(
                """INSERT INTO departments(department,active) VALUES (%s,'Yes')
                   ON CONFLICT(department) DO UPDATE SET active='Yes'""",
                (dep,)
            )

        # Existing sensitive/statutory values are preserved when the supplied file
        # leaves them blank. Populated values from the file are authoritative.
        cur.execute("""
            SELECT employee_id,bank_account,ifsc_code,aadhaar_number,salary_active
            FROM employees
        """)
        existing = {
            str(r[0]): {
                'bank_account': _clean_text(r[1]),
                'ifsc_code': _clean_text(r[2]),
                'aadhaar_number': _clean_text(r[3]),
                'salary_active': bool(r[4]) if r[4] is not None else True,
            }
            for r in cur.fetchall()
        }

        upserted = 0
        for _, row in work.iterrows():
            emp_id = str(row['__employee_id'])
            previous = existing.get(emp_id, {})
            status = _clean_text(row.get('Status')) or 'Active'
            is_active = status.strip().upper() == 'ACTIVE'
            bank_account = _clean_text(row.get('Bank Account Number')) or previous.get('bank_account','')
            ifsc_code = _clean_text(row.get('IFSC Code')) or previous.get('ifsc_code','')
            aadhaar_number = _clean_text(row.get('Aadhaar Number')) or previous.get('aadhaar_number','')
            location_code = _clean_text(row.get('LOCATION'))
            ot_applicable = _authoritative_bool(row.get('OT APPICABLE'), False)
            joining_date = normalize_date(row.get('Joining Date'))
            working_days = normalize_int(row.get('Working Days / Month'), 26)
            monthly_salary = normalize_number(row.get('Monthly Salary'), 0)
            ot_rate = normalize_number(row.get('OT Rate / Hour'), 0)
            mobile = normalize_text(row.get('Mobile Number'), '')
            email = normalize_text(row.get('Email'), '')

            cur.execute("""
                INSERT INTO employees(
                    employee_id,employee_name,department,designation,employee_type,shift,
                    skill_level,monthly_salary,ot_rate,working_days,joining_date,mobile_number,
                    email,status,remarks,division,salary_active,bank_account,ifsc_code,
                    aadhaar_number,location_code,ot_applicable
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
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
                    mobile_number=CASE WHEN excluded.mobile_number<>'' THEN excluded.mobile_number ELSE employees.mobile_number END,
                    email=CASE WHEN excluded.email<>'' THEN excluded.email ELSE employees.email END,
                    status=excluded.status,
                    remarks=excluded.remarks,
                    division=excluded.division,
                    salary_active=excluded.salary_active,
                    bank_account=CASE WHEN excluded.bank_account<>'' THEN excluded.bank_account ELSE employees.bank_account END,
                    ifsc_code=CASE WHEN excluded.ifsc_code<>'' THEN excluded.ifsc_code ELSE employees.ifsc_code END,
                    aadhaar_number=CASE WHEN excluded.aadhaar_number<>'' THEN excluded.aadhaar_number ELSE employees.aadhaar_number END,
                    location_code=excluded.location_code,
                    ot_applicable=excluded.ot_applicable
            """, (
                emp_id,
                _clean_text(row.get('Employee Name')),
                _clean_text(row.get('Department')),
                _clean_text(row.get('Designation')),
                _clean_text(row.get('Employee Type')) or 'Permanent',
                _clean_text(row.get('Shift')) or 'General',
                _clean_text(row.get('Skill Level')),
                monthly_salary,ot_rate,working_days,joining_date,mobile,email,status,
                _clean_text(row.get('Remarks')),
                str(row['__division']),
                bool(is_active),
                bank_account,ifsc_code,aadhaar_number,location_code,ot_applicable
            ))
            upserted += 1

        # Exact roster rule: employees in covered divisions but absent from the
        # authoritative file are retained for audit/history but made Inactive.
        cur.execute(
            """SELECT employee_id FROM employees
               WHERE division = ANY(%s)
                 AND status='Active'
                 AND NOT (employee_id = ANY(%s))""",
            (sync_divisions, reference_ids)
        )
        inactivated_ids = [str(r[0]) for r in cur.fetchall()]
        if inactivated_ids:
            cur.execute(
                """UPDATE employees
                   SET status='Inactive', salary_active=FALSE
                   WHERE employee_id = ANY(%s)""",
                (inactivated_ids,)
            )

        # Synchronize identity fields already stored on attendance transactions.
        attendance_synced = 0
        for _, row in work.iterrows():
            cur.execute(
                """UPDATE attendance
                   SET division=%s,
                       designation=%s,
                       source_employee_name=%s,
                       updated_at=CURRENT_TIMESTAMP
                   WHERE employee_id=%s""",
                (
                    str(row['__division']),
                    _clean_text(row.get('Designation')),
                    _clean_text(row.get('Employee Name')),
                    str(row['__employee_id'])
                )
            )
            attendance_synced += int(cur.rowcount or 0)

        # Reconcile only master-related HR reviews. Genuine biometric exceptions
        # (PA/AP or incomplete PP punches) remain in HR Review.
        cur.execute(
            """SELECT id,employee_id,raw_status,working_hours,time_in,time_out,day_name,
                      status,review_required,COALESCE(source_issue,''),COALESCE(remark,'')
               FROM attendance
               WHERE employee_id = ANY(%s)
                 AND COALESCE(source_issue,'')<>''""",
            (reference_ids,)
        )
        exception_rows = cur.fetchall()
        resolved_master_reviews = 0
        remaining_biometric_reviews = 0
        for att in exception_rows:
            att_id, emp_id, raw_status, working_hours, time_in, time_out, day_name, old_status, old_review, source_issue, remark = att
            final_status = _map_attendance_status(
                raw_status, working_hours, time_in, time_out, day_name
            )
            review_required = final_status == 'HR Review'
            cur.execute(
                """UPDATE attendance
                   SET status=%s,
                       review_required=%s,
                       source_issue='',
                       reviewed_by=CASE WHEN %s=FALSE THEN %s ELSE reviewed_by END,
                       updated_at=CURRENT_TIMESTAMP
                   WHERE id=%s""",
                (final_status, review_required, review_required, str(updated_by), int(att_id))
            )
            if review_required:
                remaining_biometric_reviews += 1
            else:
                resolved_master_reviews += 1

        # Pending placeholder departments are no longer real master records after
        # the roster sync; missing IDs were already made inactive above.
        cur.execute("""
            UPDATE employees
            SET status='Inactive', salary_active=FALSE
            WHERE division = ANY(%s)
              AND LOWER(TRIM(COALESCE(department,'')))='hr review'
              AND NOT (employee_id = ANY(%s))
        """, (sync_divisions, reference_ids))

        conn.commit()
        cur.close()
        return {
            'master_rows': upserted,
            'active_reference_employees': int(
                sum(1 for _, r in work.iterrows() if _clean_text(r.get('Status')).upper() == 'ACTIVE')
            ),
            'inactivated_not_in_file': len(inactivated_ids),
            'attendance_rows_synced': attendance_synced,
            'master_reviews_resolved': resolved_master_reviews,
            'biometric_reviews_remaining': remaining_biometric_reviews,
            'departments_from_file': len(exact_departments),
            'divisions_synced': len(sync_divisions),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
'''

text = text.replace(helper_marker, helpers + helper_marker, 1)

# ------------------------------------------------------------------
# 2) Prevent the old V7 mapping routine from rewriting employee rows.
# ------------------------------------------------------------------
legacy_update = '''                # Case-insensitive update handles old capitalization variants\n                # such as FG-Samsung / Fg-Samsung and Sales / sales.\n                cur.execute(\n                    """UPDATE employees\n                       SET department=%s\n                       WHERE LOWER(TRIM(department))=LOWER(TRIM(%s))""",\n                    (_target_dep,_source_dep)\n                )\n\n'''
legacy_replacement = '''                # Authoritative Employee Master rule: legacy mappings may remain\n                # as reference configuration, but they must never rewrite current\n                # Employee Master department values automatically.\n\n'''
if legacy_update in text:
    text = text.replace(legacy_update, legacy_replacement, 1)

# ------------------------------------------------------------------
# 3) Add a dedicated one-click Authoritative Master workspace.
# ------------------------------------------------------------------
old_options = '''        master_options=[\n            "Fresh Live Start",\n            "Universal Master Import",\n            "Employee Master",\n'''
new_options = '''        master_options=[\n            "Fresh Live Start",\n            "Universal Master Import",\n            "Authoritative Employee Master Sync",\n            "Employee Master",\n'''
if old_options not in text:
    raise SystemExit('master options anchor not found')
text = text.replace(old_options, new_options, 1)

employee_marker = '''        # ----------------------------------------------------\n        # EMPLOYEE MASTER\n        # ----------------------------------------------------\n        elif master_area=="Employee Master":\n'''
if employee_marker not in text:
    raise SystemExit('employee master UI marker not found')

authoritative_ui = r'''        # ----------------------------------------------------
        # AUTHORITATIVE EMPLOYEE MASTER SYNC
        # ----------------------------------------------------
        elif master_area=="Authoritative Employee Master Sync":
            v5_panel(
                "Authoritative Employee Master Sync",
                "Restore Employee Master exactly from the supplied Employee_Data XLSX, then reconcile attendance identity and master-only HR exceptions."
            )
            st.info(
                "This mode keeps Department names exactly as written in the workbook. "
                "No automatic department mapping is applied. Employees in the covered divisions who are not in the workbook are kept for audit history but marked Inactive."
            )
            st.caption(
                "It updates Employee Name, Department, Designation, Employee Type, Shift, Skill Level, Monthly Salary, "
                "Working Days, OT Rate, Joining Date, Status, Remarks and Location/Division. Blank mobile/bank/statutory fields do not erase existing values."
            )

            authoritative_file = st.file_uploader(
                "Upload Authoritative Employee Master XLSX",
                type=["xlsx"],
                key="v100_authoritative_master_upload"
            )

            if authoritative_file is not None:
                try:
                    authoritative_file.seek(0)
                    check = preview_authoritative_employee_master_excel(authoritative_file)
                    a1,a2,a3,a4 = st.columns(4)
                    a1.metric("Employees", f"{check['employees']:,}")
                    a2.metric("Divisions", f"{check['divisions']:,}")
                    a3.metric("Departments", f"{check['departments']:,}")
                    a4.metric("Validation Errors", f"{len(check['errors']):,}")

                    st.markdown("#### Division Check")
                    st.dataframe(check['location_summary'], hide_index=True, use_container_width=True)

                    with st.expander("Department Check", expanded=False):
                        st.dataframe(check['department_summary'], hide_index=True, use_container_width=True, height=420)

                    with st.expander("Employee Preview", expanded=True):
                        st.dataframe(check['preview'], hide_index=True, use_container_width=True, height=480)

                    if check['errors']:
                        st.error("Employee Master validation failed. Nothing has been changed.")
                        for err in check['errors'][:100]:
                            st.write("• " + err)
                    else:
                        st.success(
                            "Workbook is valid. Department values will be kept exactly as supplied. "
                            "Attendance history will be linked to these Employee IDs without deleting historical transactions."
                        )
                        confirm_authoritative = st.checkbox(
                            "I confirm this workbook is the authoritative active Employee Master. Employees in these divisions who are missing from the file may be marked Inactive.",
                            key="v100_authoritative_confirm"
                        )
                        if st.button(
                            "Sync Employee Master & Attendance",
                            type="primary",
                            use_container_width=True,
                            disabled=not confirm_authoritative,
                            key="v100_authoritative_sync_btn"
                        ):
                            authoritative_file.seek(0)
                            with st.spinner("Synchronizing Employee Master and attendance safely..."):
                                result = sync_authoritative_employee_master_excel(
                                    authoritative_file, _current_user['username']
                                )
                            st.success(
                                f"Employee Master synchronized: {result['master_rows']:,} workbook employee(s) processed; "
                                f"{result['inactivated_not_in_file']:,} employee(s) not in the file marked Inactive."
                            )
                            r1,r2,r3,r4 = st.columns(4)
                            r1.metric("Master Employees", f"{result['master_rows']:,}")
                            r2.metric("Attendance Rows Synced", f"{result['attendance_rows_synced']:,}")
                            r3.metric("Master Reviews Resolved", f"{result['master_reviews_resolved']:,}")
                            r4.metric("Biometric Reviews Left", f"{result['biometric_reviews_remaining']:,}")
                            st.info(
                                "Next: open Employees → Directory / Employee 360 and Attendance → HR Review. "
                                "Only genuine biometric exceptions should remain for HR action."
                            )
                            st.session_state['v100_authoritative_sync_done'] = True
                            st.rerun()
                except Exception as exc:
                    st.error(f"Authoritative Employee Master sync failed: {exc}")

'''

text = text.replace(employee_marker, authoritative_ui + employee_marker, 1)

p.write_text(text, encoding='utf-8')
