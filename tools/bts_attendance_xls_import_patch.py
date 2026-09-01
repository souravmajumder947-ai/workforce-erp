from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

start = text.find('def _read_standard_attendance_upload(uploaded_file):')
end = text.find('\ndef detect_standard_attendance_file_division', start)
if start < 0 or end < 0:
    raise SystemExit('attendance reader anchors not found')

new_func = r'''def _read_standard_attendance_upload(uploaded_file):
    """Read standard attendance exports without changing the source portal.

    Supports CSV, XLSX and legacy XLS. BTS attendance exports may be a real
    Excel .xls file or an HTML table saved with an .xls extension; both are
    handled here as read-only uploads into Reliable HRMS.
    """
    filename = _clean_text(getattr(uploaded_file, "name", "")).lower()

    def _clean_candidate(table):
        if table is None or table.empty:
            return table
        table = table.copy()
        if isinstance(table.columns, pd.MultiIndex):
            table.columns = [
                _clean_text(" ".join(str(x) for x in col if _clean_text(x)))
                for col in table.columns
            ]
        else:
            table.columns = [_clean_text(c) for c in table.columns]

        mapped = _attendance_column_map(table.columns)
        if mapped.get("employee_id") and mapped.get("date"):
            return table

        # Some report exports place company/report headings above the true header.
        for idx in range(min(35, len(table))):
            row_values = [_clean_text(v) for v in table.iloc[idx].tolist()]
            keys = {_attendance_col_key(v) for v in row_values if v}
            has_emp = bool(keys & ATTENDANCE_COLUMN_ALIASES["employee_id"])
            has_date = bool(keys & ATTENDANCE_COLUMN_ALIASES["date"])
            if has_emp and has_date:
                promoted = table.iloc[idx + 1:].copy()
                promoted.columns = row_values
                promoted.columns = [_clean_text(c) for c in promoted.columns]
                return promoted
        return table

    uploaded_file.seek(0)
    if filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
        return _clean_candidate(df)

    if filename.endswith(".xls"):
        raw_bytes = uploaded_file.read()
        if not raw_bytes:
            raise ValueError("The XLS attendance file is empty.")
        probe = raw_bytes[:50000].lstrip().lower()
        html_like = probe.startswith(b"<") or b"<table" in probe or b"<html" in probe

        if html_like:
            try:
                tables = pd.read_html(BytesIO(raw_bytes), header=0)
            except Exception as exc:
                raise ValueError(
                    "Unable to read the BTS XLS/HTML attendance export. "
                    f"Please download the report again: {exc}"
                ) from exc
            candidates = [_clean_candidate(t) for t in tables if t is not None and not t.empty]
            valid = [
                t for t in candidates
                if t is not None
                and _attendance_column_map(t.columns).get("employee_id")
                and _attendance_column_map(t.columns).get("date")
            ]
            if valid:
                return max(valid, key=len)
            if candidates:
                return max(candidates, key=len)
            raise ValueError("No attendance table was found in the BTS XLS export.")

        # Genuine legacy binary .xls workbook.
        try:
            uploaded_file.seek(0)
            raw = pd.read_excel(uploaded_file, header=None, engine="xlrd")
        except Exception as exc:
            raise ValueError(
                "Unable to read the legacy XLS attendance file. "
                f"Please download it again from BTS: {exc}"
            ) from exc

        header_idx = 0
        found = False
        for idx in range(min(35, len(raw))):
            keys = {_attendance_col_key(v) for v in raw.iloc[idx].tolist() if _clean_text(v)}
            if bool(keys & ATTENDANCE_COLUMN_ALIASES["employee_id"]) and bool(keys & ATTENDANCE_COLUMN_ALIASES["date"]):
                header_idx = idx
                found = True
                break
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, header=header_idx, engine="xlrd")
        df.columns = [_clean_text(c) for c in df.columns]
        return df

    # XLSX: find a header row that contains Employee_ID / Employee Code / PayCode.
    uploaded_file.seek(0)
    raw = pd.read_excel(uploaded_file, header=None, engine="openpyxl")
    header_idx = 0
    found = False
    for idx in range(min(35, len(raw))):
        keys = {_attendance_col_key(v) for v in raw.iloc[idx].tolist() if _clean_text(v)}
        has_emp = bool(keys & ATTENDANCE_COLUMN_ALIASES["employee_id"])
        has_date = bool(keys & ATTENDANCE_COLUMN_ALIASES["date"])
        if has_emp and has_date:
            header_idx = idx
            found = True
            break

    uploaded_file.seek(0)
    df = pd.read_excel(uploaded_file, header=header_idx, engine="openpyxl")
    df.columns = [_clean_text(c) for c in df.columns]
    return df
'''

text = text[:start] + new_func + text[end:]

old_upload = '''            attendance_file = st.file_uploader(
                "Attendance File (CSV or XLSX)",
                type=["csv","xlsx"],
                key="v5_att_upload"
            )'''
new_upload = '''            attendance_file = st.file_uploader(
                "Attendance File (BTS CSV / XLS / XLSX)",
                type=["csv","xls","xlsx"],
                key="v5_att_upload",
                help="Download the Attendance Report from BTS and upload it here. This is read-only and does not change the BTS portal."
            )'''
if old_upload not in text:
    raise SystemExit('attendance uploader anchor not found')
text = text.replace(old_upload, new_upload, 1)

p.write_text(text, encoding='utf-8')
