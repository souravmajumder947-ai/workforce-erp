from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V11.6 PRODUCTION ENTRY FIRST"
if MARK in s:
    print("V11.6 Production Entry already applied")
    raise SystemExit(0)

old_head = '''elif page == "Operations":
    v5_page_header(
        "Plant Operations",
        "Corrugation is measured against a fixed ton target; conversion machines are measured against 100% material flow.",
        "Greater Noida Plant",global_work_date
    )
    tab_prod,tab_mp=st.tabs(["Production Flow","Manpower Allocation"])

    with tab_prod:
        c1,c2,c3=st.columns(3)
'''

new_head = '''elif page == "Operations":
    # V11.6 PRODUCTION ENTRY FIRST
    v5_page_header(
        "Production & Plant Operations",
        "Enter production first. Corrugation uses a fixed-ton target; downstream machines use material-conversion flow.",
        "Greater Noida Plant",global_work_date
    )
    tab_prod,tab_mp=st.tabs(["Production Entry","Manpower Allocation"])

    with tab_prod:
        st.markdown("### Production Entry")
        st.caption(
            "Select Date → Shift → Machine. Existing entries are loaded automatically and can be safely updated."
        )
        c1,c2,c3=st.columns(3)
'''

if old_head not in s:
    raise RuntimeError("Operations header anchor not found")
s = s.replace(old_head, new_head, 1)

old_existing = '''            er=existing.iloc[0].to_dict() if not existing.empty else {}
            std,shift_target=get_machine_shift_target(machine,shift)

            if target_type=="FIXED_TON":
'''

new_existing = '''            er=existing.iloc[0].to_dict() if not existing.empty else {}
            std,shift_target=get_machine_shift_target(machine,shift)

            _prod_master_row = machine_df[machine_df["machine"].astype(str) == str(machine)]
            _prod_department = (
                str(_prod_master_row.iloc[0].get("department") or "—")
                if not _prod_master_row.empty else "—"
            )
            pinfo1,pinfo2,pinfo3,pinfo4 = st.columns(4)
            pinfo1.metric("Division","Greater Noida Plant")
            pinfo2.metric("Department",_prod_department)
            pinfo3.metric("Machine",str(machine))
            pinfo4.metric("Entry Status","Update Existing" if not existing.empty else "New Entry")
            if not existing.empty:
                st.info(
                    f"An entry already exists for {pdate.strftime('%d/%m/%Y')} · Shift {shift} · {machine}. "
                    "Saving will update that same production record, not create a duplicate."
                )

            if target_type=="FIXED_TON":
'''

if old_existing not in s:
    raise RuntimeError("Production existing-entry anchor not found")
s = s.replace(old_existing, new_existing, 1)

old_fixed_button = '''                    save_prod=st.form_submit_button("Save Corrugation Production",type="primary",use_container_width=True)
'''
new_fixed_button = '''                    save_prod=st.form_submit_button("Save / Update Production Entry",type="primary",use_container_width=True)
'''
if old_fixed_button not in s:
    raise RuntimeError("Corrugation save button anchor not found")
s = s.replace(old_fixed_button, new_fixed_button, 1)

old_fixed_success = '''                    st.success("Corrugation production saved.")
                    st.rerun()
'''
new_fixed_success = '''                    record_audit_event(
                        _current_user["username"], "PRODUCTION_SAVE", "Operations",
                        "Production", f"{pdate.isoformat()}|{shift}|{machine}",
                        f"Type=FIXED_TON; Output={good_output:.2f}; Target={shift_target:.2f}; Waste={waste_ton:.2f}; Breakdown={breakdown_hours:.2f}"
                    )
                    st.success("Production entry saved successfully.")
                    st.rerun()
'''
if old_fixed_success not in s:
    raise RuntimeError("Corrugation save success anchor not found")
s = s.replace(old_fixed_success, new_fixed_success, 1)

old_conversion_button = '''                    save_prod=st.form_submit_button("Save Conversion Production",type="primary",use_container_width=True)
'''
new_conversion_button = '''                    save_prod=st.form_submit_button("Save / Update Production Entry",type="primary",use_container_width=True)
'''
if old_conversion_button not in s:
    raise RuntimeError("Conversion save button anchor not found")
s = s.replace(old_conversion_button, new_conversion_button, 1)

old_conversion_success = '''                        st.success("Conversion production saved.")
                        st.rerun()
'''
new_conversion_success = '''                        record_audit_event(
                            _current_user["username"], "PRODUCTION_SAVE", "Operations",
                            "Production", f"{pdate.isoformat()}|{shift}|{machine}",
                            (
                                f"Type=MATERIAL_CONVERSION; Available={available:.2f}; Processed={material_processed:.2f}; "
                                f"Good={good_output:.2f}; Waste={waste_ton:.2f}; Closing={closing:.2f}; "
                                f"Conversion={conversion_pct:.2f}%; Yield={yield_pct:.2f}%"
                            )
                        )
                        st.success("Production entry saved successfully.")
                        st.rerun()
'''
if old_conversion_success not in s:
    raise RuntimeError("Conversion save success anchor not found")
s = s.replace(old_conversion_success, new_conversion_success, 1)

old_day = '''        prod_day=read_df(
            """SELECT p.work_date,p.shift,p.machine,m.department,m.target_type,
                      p.production_ton,p.target_ton,p.opening_wip_ton,p.material_received_ton,
                      p.material_available_ton,p.material_processed_ton,p.good_output_ton,
                      p.closing_wip_ton,p.waste_ton,p.conversion_pct,p.yield_pct,p.waste_pct,
                      p.breakdown_hours,p.remark
               FROM production p LEFT JOIN machines m ON m.machine=p.machine
               WHERE p.work_date=? ORDER BY p.shift,p.machine""",
            (global_work_date.isoformat(),)
        )
        if not prod_day.empty:
            display=prod_day.rename(columns={
'''

new_day = '''        # The daily summary follows the Production Date selected above, not the global Working Date.
        prod_day=read_df(
            """SELECT p.work_date,p.shift,p.machine,m.department,m.target_type,
                      p.production_ton,p.target_ton,p.opening_wip_ton,p.material_received_ton,
                      p.material_available_ton,p.material_processed_ton,p.good_output_ton,
                      p.closing_wip_ton,p.waste_ton,p.conversion_pct,p.yield_pct,p.waste_pct,
                      p.breakdown_hours,p.remark
               FROM production p LEFT JOIN machines m ON m.machine=p.machine
               WHERE p.work_date=? ORDER BY p.shift,p.machine""",
            (pdate.isoformat(),)
        )
        if not prod_day.empty:
            _pd_good = pd.to_numeric(
                prod_day["good_output_ton"].where(
                    pd.to_numeric(prod_day["good_output_ton"], errors="coerce").fillna(0) > 0,
                    prod_day["production_ton"]
                ),
                errors="coerce"
            ).fillna(0)
            _pd_waste = pd.to_numeric(prod_day["waste_ton"], errors="coerce").fillna(0)
            _pd_break = pd.to_numeric(prod_day["breakdown_hours"], errors="coerce").fillna(0)
            _pd_fixed = prod_day[prod_day["target_type"].astype(str) == "FIXED_TON"].copy()
            _pd_fixed_output = (
                pd.to_numeric(_pd_fixed["good_output_ton"], errors="coerce").fillna(0)
                if not _pd_fixed.empty else pd.Series(dtype=float)
            )
            if not _pd_fixed.empty:
                _pd_fixed_output = _pd_fixed_output.where(
                    _pd_fixed_output > 0,
                    pd.to_numeric(_pd_fixed["production_ton"], errors="coerce").fillna(0)
                )
            _pd_fixed_target = (
                pd.to_numeric(_pd_fixed["target_ton"], errors="coerce").fillna(0).sum()
                if not _pd_fixed.empty else 0.0
            )
            _pd_fixed_achievement = (
                float(_pd_fixed_output.sum()) / float(_pd_fixed_target) * 100.0
                if float(_pd_fixed_target) > 0 else 0.0
            )

            st.markdown(f"#### Production Summary · {pdate.strftime('%d %b %Y')}")
            ds1,ds2,ds3,ds4,ds5 = st.columns(5)
            ds1.metric("Entries",f"{len(prod_day):,}")
            ds2.metric("Good Output",f"{float(_pd_good.sum()):.2f} T")
            ds3.metric("Waste / Rejection",f"{float(_pd_waste.sum()):.2f} T")
            ds4.metric("Breakdown",f"{float(_pd_break.sum()):.2f} Hrs")
            ds5.metric("Corrugation Achievement",f"{_pd_fixed_achievement:.2f}%")

            display=prod_day.rename(columns={
'''

if old_day not in s:
    raise RuntimeError("Daily production summary anchor not found")
s = s.replace(old_day, new_day, 1)

old_title = '''            st.markdown("#### Daily Production Flow")
            st.dataframe(display,hide_index=True,use_container_width=True)
'''
new_title = '''            st.markdown("#### Saved Production Entries")
            st.dataframe(display,hide_index=True,use_container_width=True)
        else:
            st.info(f"No production entry is saved for {pdate.strftime('%d/%m/%Y')} yet.")
'''
if old_title not in s:
    raise RuntimeError("Daily production table title anchor not found")
s = s.replace(old_title, new_title, 1)

p.write_text(s, encoding="utf-8")
print("Applied V11.6 Production Entry first")
