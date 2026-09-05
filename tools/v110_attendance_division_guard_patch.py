from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V11.0 ATTENDANCE DIVISION SAFETY GUARD"
if MARK in s:
    print("V11.0 attendance division guard already applied")
    raise SystemExit(0)

# Enrich attendance precheck with row-level mismatch counts and an Employee-Master majority suggestion.
old_result = '''    result = {
        "rows_ready": 0, "employees": 0, "dates": 0, "duplicates": 0,
        "unknown_ids": [], "division_mismatches": [], "inactive_ids": [],
        "inactive_rows": 0, "hr_review": 0,
        "master_exception_rows": 0, "status_summary": pd.DataFrame()
    }'''
new_result = '''    # V11.0 ATTENDANCE DIVISION SAFETY GUARD
    result = {
        "rows_ready": 0, "employees": 0, "dates": 0, "duplicates": 0,
        "unknown_ids": [], "division_mismatches": [], "division_mismatch_ids": [],
        "division_mismatch_rows": 0, "inactive_ids": [],
        "inactive_rows": 0, "hr_review": 0,
        "master_exception_rows": 0, "status_summary": pd.DataFrame(),
        "suggested_division": "", "suggested_division_employees": 0,
        "suggested_division_pct": 0.0,
    }'''
if old_result not in s:
    raise RuntimeError("attendance_precheck result anchor not found")
s = s.replace(old_result, new_result, 1)

old_lists = '''    unknown, mismatch, inactive = [], [], []
    exception_mask, inactive_mask = [], []
'''
new_lists = '''    unknown, mismatch, mismatch_ids, inactive = [], [], [], []
    mismatch_row_count = 0
    known_active_ids_by_division = {}
    exception_mask, inactive_mask = [], []
'''
if old_lists not in s:
    raise RuntimeError("attendance_precheck list anchor not found")
s = s.replace(old_lists, new_lists, 1)

old_loop_piece = '''        if emp_master and master_status in {"INACTIVE", "LEFT", "RESIGNED", "TERMINATED"}:
            inactive.append(eid)
            is_inactive = True
        elif not emp_master or emp_master.get("department", "").upper() == "HR REVIEW":
            unknown.append(eid)
            has_issue = True
        elif emp_master.get("division") and div and emp_master.get("division") != div:
            mismatch.append(f"{eid}: master={emp_master.get('division')}, file={div}")
            has_issue = True

        exception_mask.append(has_issue)
'''
new_loop_piece = '''        if emp_master and master_status in {"INACTIVE", "LEFT", "RESIGNED", "TERMINATED"}:
            inactive.append(eid)
            is_inactive = True
        elif not emp_master or emp_master.get("department", "").upper() == "HR REVIEW":
            unknown.append(eid)
            has_issue = True
        else:
            master_division = _clean_text(emp_master.get("division"))
            if master_division and eid:
                known_active_ids_by_division.setdefault(master_division, set()).add(eid)
            if master_division and div and master_division != div:
                mismatch.append(f"{eid}: master={master_division}, file={div}")
                mismatch_ids.append(eid)
                mismatch_row_count += 1
                has_issue = True

        exception_mask.append(has_issue)
'''
if old_loop_piece not in s:
    raise RuntimeError("attendance_precheck mismatch loop anchor not found")
s = s.replace(old_loop_piece, new_loop_piece, 1)

old_assign = '''    result["unknown_ids"] = sorted(set(x for x in unknown if x))
    result["division_mismatches"] = sorted(set(mismatch))
    result["inactive_ids"] = sorted(set(x for x in inactive if x))
'''
new_assign = '''    result["unknown_ids"] = sorted(set(x for x in unknown if x))
    result["division_mismatches"] = sorted(set(mismatch))
    result["division_mismatch_ids"] = sorted(set(x for x in mismatch_ids if x))
    result["division_mismatch_rows"] = int(mismatch_row_count)
    result["inactive_ids"] = sorted(set(x for x in inactive if x))

    if known_active_ids_by_division:
        suggested_division, suggested_ids = max(
            known_active_ids_by_division.items(),
            key=lambda item: len(item[1])
        )
        known_active_total = len(set().union(*known_active_ids_by_division.values()))
        result["suggested_division"] = suggested_division
        result["suggested_division_employees"] = len(suggested_ids)
        result["suggested_division_pct"] = (
            (len(suggested_ids) / known_active_total * 100.0)
            if known_active_total else 0.0
        )
'''
if old_assign not in s:
    raise RuntimeError("attendance_precheck assignment anchor not found")
s = s.replace(old_assign, new_assign, 1)

# Replace the current mismatch warning + hard error calculation with a proper guard.
old_ui = '''                    if precheck["division_mismatches"]:
                        st.warning(
                            "Division mismatch rows will be imported as HR Review: "
                            + " | ".join(precheck["division_mismatches"][:12])
                        )

                    hard_errors = precheck["duplicates"] > 0

                    if not hard_errors:
'''
new_ui = '''                    division_guard_block = False
                    if precheck["division_mismatches"]:
                        _v110_mismatch_rows = int(precheck.get("division_mismatch_rows", 0))
                        _v110_mismatch_ids = list(precheck.get("division_mismatch_ids", []))
                        _v110_rows_ready = max(int(precheck.get("rows_ready", 0)), 1)
                        _v110_mismatch_pct = (_v110_mismatch_rows / _v110_rows_ready) * 100.0
                        _v110_suggested = _clean_text(precheck.get("suggested_division"))
                        _v110_suggested_count = int(precheck.get("suggested_division_employees", 0))
                        _v110_suggested_pct = float(precheck.get("suggested_division_pct", 0.0))

                        # Block when the file looks structurally assigned to another division.
                        # Small one-off transfer/mapping exceptions can still go to HR Review.
                        division_guard_block = bool(
                            (
                                len(_v110_mismatch_ids) >= 2
                                and _v110_mismatch_rows >= 10
                                and _v110_mismatch_pct >= 25.0
                            )
                            or (
                                _v110_suggested
                                and _v110_suggested != actual
                                and _v110_suggested_count >= 2
                                and _v110_suggested_pct >= 60.0
                            )
                        )

                        if division_guard_block:
                            st.error(
                                "🛑 **IMPORT BLOCKED — Possible wrong division selected.**  "
                                f"{_v110_mismatch_rows:,} row(s) across {len(_v110_mismatch_ids):,} employee(s) "
                                f"conflict with Employee Master ({_v110_mismatch_pct:.1f}% of importable rows). "
                                + (
                                    f"Employee Master indicates this file most likely belongs to **{_v110_suggested}** "
                                    f"({_v110_suggested_count} employee(s), {_v110_suggested_pct:.1f}% of known active IDs). "
                                    if _v110_suggested else ""
                                )
                                + "The app will not create bulk false HR Review rows. Correct the division and preview again."
                            )
                            st.caption(
                                "Mismatch examples: "
                                + " | ".join(precheck["division_mismatches"][:8])
                            )

                            if _v110_suggested in DIVISIONS and _v110_suggested != expected:
                                def _v110_switch_expected_division():
                                    st.session_state["v5_att_expected"] = _v110_suggested
                                    st.session_state["v69_attendance_confirm"] = False

                                _v110_switch_clicked = st.button(
                                    f"Use {_v110_suggested} and Recheck",
                                    key="v110_use_suggested_division",
                                    type="primary",
                                    use_container_width=True,
                                    on_click=_v110_switch_expected_division,
                                )
                        else:
                            st.warning(
                                f"{_v110_mismatch_rows:,} limited division-mismatch row(s) detected. "
                                "These will be routed to HR Review for HR verification: "
                                + " | ".join(precheck["division_mismatches"][:12])
                            )

                    hard_errors = (precheck["duplicates"] > 0) or division_guard_block

                    if division_guard_block:
                        st.info(
                            "Import controls are locked until the division mismatch is corrected. "
                            "No attendance rows have been saved from this preview."
                        )

                    if not hard_errors:
'''
if old_ui not in s:
    raise RuntimeError("attendance import mismatch UI anchor not found")
s = s.replace(old_ui, new_ui, 1)

p.write_text(s, encoding="utf-8")
print("Applied V11.0 attendance division safety guard")
