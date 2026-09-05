from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V11.7 CORRUGATION MATERIAL BALANCE ENTRY"
if MARK in s:
    print("V11.7 Corrugation material-balance entry already applied")
    raise SystemExit(0)

old = '''            if target_type=="FIXED_TON":
                daily_target=float(profile.get("daily_target_ton") or 0)
                if shift_target<=0:
                    shift_target=daily_target/2.0
                st.info(
                    f"🎯 **Fixed Ton Target** · Daily target: **{daily_target:.2f} T** · "
                    f"{shift} shift target: **{shift_target:.2f} T**"
                )
                with st.form("v66_fixed_prod_form"):
                    c1,c2,c3=st.columns(3)
                    good_output=c1.number_input(
                        "Good Production Ton",min_value=0.0,
                        value=float(er.get("good_output_ton") or er.get("production_ton") or 0),step=0.1
                    )
                    waste_ton=c2.number_input(
                        "Waste / Rejection Ton",min_value=0.0,
                        value=float(er.get("waste_ton") or 0),step=0.1
                    )
                    breakdown_hours=c3.number_input(
                        "Breakdown Hours",min_value=0.0,max_value=24.0,
                        value=float(er.get("breakdown_hours") or 0),step=0.25
                    )
                    remark=st.text_input("Production Remark",value=str(er.get("remark") or ""))
                    save_prod=st.form_submit_button("Save / Update Production Entry",type="primary",use_container_width=True)

                achievement=(good_output/shift_target*100.0) if shift_target>0 else 0.0
                k1,k2,k3,k4=st.columns(4)
                k1.metric("Good Output",f"{good_output:.2f} T")
                k2.metric("Shift Target",f"{shift_target:.2f} T")
                k3.metric("Achievement",f"{achievement:.2f}%")
                k4.metric("Waste",f"{waste_ton:.2f} T")

                if save_prod:
                    upsert(
                        """INSERT INTO production(
                           work_date,shift,machine,production_ton,target_ton,waste_ton,breakdown_hours,
                           paper_cost,ink_cost,glue_cost,other_material_cost,target_type,
                           opening_wip_ton,material_received_ton,material_available_ton,
                           material_processed_ton,good_output_ton,closing_wip_ton,
                           conversion_pct,yield_pct,waste_pct,remark
                           ) VALUES (?,?,?,?,?,?,?,0,0,0,0,?,0,0,0,0,?,0,0,0,?,?)
                           ON CONFLICT(work_date,shift,machine) DO UPDATE SET
                           production_ton=excluded.production_ton,target_ton=excluded.target_ton,
                           waste_ton=excluded.waste_ton,breakdown_hours=excluded.breakdown_hours,
                           target_type=excluded.target_type,good_output_ton=excluded.good_output_ton,
                           waste_pct=excluded.waste_pct,remark=excluded.remark""",
                        (
                            pdate.isoformat(),shift,machine,good_output,shift_target,waste_ton,
                            breakdown_hours,"FIXED_TON",good_output,
                            (waste_ton/(good_output+waste_ton)*100.0) if (good_output+waste_ton)>0 else 0.0,
                            remark
                        )
                    )
                    record_audit_event(
                        _current_user["username"], "PRODUCTION_SAVE", "Operations",
                        "Production", f"{pdate.isoformat()}|{shift}|{machine}",
                        f"Type=FIXED_TON; Output={good_output:.2f}; Target={shift_target:.2f}; Waste={waste_ton:.2f}; Breakdown={breakdown_hours:.2f}"
                    )
                    st.success("Production entry saved successfully.")
                    st.rerun()
'''

new = '''            if target_type=="FIXED_TON":
                # V11.7 CORRUGATION MATERIAL BALANCE ENTRY
                daily_target=float(profile.get("daily_target_ton") or 0)
                if shift_target<=0:
                    shift_target=daily_target/2.0
                st.info(
                    f"🎯 **Corrugation Fixed Ton Target** · Daily target: **{daily_target:.2f} T** · "
                    f"{shift} shift target: **{shift_target:.2f} T**"
                )
                st.caption(
                    "Enter actual paper consumed and usable corrugated output. The system calculates "
                    "target achievement, yield, waste percentage and material variance automatically."
                )

                _existing_paper_consumed = float(er.get("material_processed_ton") or 0)
                _existing_good = float(er.get("good_output_ton") or er.get("production_ton") or 0)
                _existing_waste = float(er.get("waste_ton") or 0)
                _existing_remark = str(er.get("remark") or "")
                _existing_break_reason = ""
                _existing_prod_remark = _existing_remark
                if "Breakdown Reason:" in _existing_remark:
                    _parts = _existing_remark.split("Breakdown Reason:",1)
                    _existing_prod_remark = _parts[0].strip(" |")
                    _existing_break_reason = _parts[1].strip()

                with st.form("v66_fixed_prod_form"):
                    c1,c2,c3,c4=st.columns(4)
                    paper_consumed=c1.number_input(
                        "Paper Consumed Ton",min_value=0.0,
                        value=_existing_paper_consumed,step=0.1,
                        help="Actual paper consumed / processed by corrugation in this shift."
                    )
                    good_output=c2.number_input(
                        "Good Corrugated Output Ton",min_value=0.0,
                        value=_existing_good,step=0.1,
                        help="Usable corrugated board produced in this shift."
                    )
                    waste_ton=c3.number_input(
                        "Waste / Rejection Ton",min_value=0.0,
                        value=_existing_waste,step=0.1,
                        help="Actual paper/process waste or rejection recorded for this shift."
                    )
                    breakdown_hours=c4.number_input(
                        "Breakdown Hours",min_value=0.0,max_value=24.0,
                        value=float(er.get("breakdown_hours") or 0),step=0.25
                    )
                    breakdown_reason=st.text_input(
                        "Breakdown Reason",
                        value=_existing_break_reason,
                        placeholder="Required when Breakdown Hours is greater than 0"
                    )
                    remark=st.text_input(
                        "Production Remark",
                        value=_existing_prod_remark,
                        placeholder="Optional production / quality remark"
                    )
                    save_prod=st.form_submit_button(
                        "Save / Update Corrugation Production",
                        type="primary",use_container_width=True
                    )

                achievement=(good_output/shift_target*100.0) if shift_target>0 else 0.0
                yield_pct=(good_output/paper_consumed*100.0) if paper_consumed>0 else 0.0
                waste_pct=(waste_ton/paper_consumed*100.0) if paper_consumed>0 else 0.0
                material_variance=paper_consumed-good_output-waste_ton
                expected_waste=max(paper_consumed-good_output,0.0)

                k1,k2,k3,k4,k5=st.columns(5)
                k1.metric("Shift Target",f"{shift_target:.2f} T")
                k2.metric("Achievement",f"{achievement:.2f}%")
                k3.metric("Yield",f"{yield_pct:.2f}%")
                k4.metric("Waste",f"{waste_pct:.2f}%")
                k5.metric("Material Variance",f"{material_variance:.2f} T")

                m1,m2,m3=st.columns(3)
                m1.metric("Paper Consumed",f"{paper_consumed:.2f} T")
                m2.metric("Good Output",f"{good_output:.2f} T")
                m3.metric("Expected Balance Waste",f"{expected_waste:.2f} T")

                if paper_consumed>0 and abs(material_variance)>0.01:
                    st.warning(
                        f"Material balance variance is {material_variance:.2f} T. "
                        "Paper Consumed should normally equal Good Output + Waste/Rejection. "
                        "Please verify the entry before saving."
                    )

                if save_prod:
                    _fixed_errors=[]
                    if paper_consumed<=0 and (good_output>0 or waste_ton>0):
                        _fixed_errors.append("Paper Consumed must be greater than 0 when production or waste is entered.")
                    if good_output+waste_ton > paper_consumed + 0.01:
                        _fixed_errors.append(
                            "Good Output + Waste/Rejection cannot be greater than Paper Consumed."
                        )
                    if breakdown_hours>0 and not str(breakdown_reason or "").strip():
                        _fixed_errors.append("Breakdown Reason is required when Breakdown Hours is greater than 0.")

                    if _fixed_errors:
                        for _err in _fixed_errors:
                            st.error(_err)
                    else:
                        _save_remark=str(remark or "").strip()
                        if breakdown_hours>0:
                            _br=str(breakdown_reason or "").strip()
                            _save_remark=(
                                f"{_save_remark} | Breakdown Reason: {_br}"
                                if _save_remark else f"Breakdown Reason: {_br}"
                            )

                        upsert(
                            """INSERT INTO production(
                               work_date,shift,machine,production_ton,target_ton,waste_ton,breakdown_hours,
                               paper_cost,ink_cost,glue_cost,other_material_cost,target_type,
                               opening_wip_ton,material_received_ton,material_available_ton,
                               material_processed_ton,good_output_ton,closing_wip_ton,
                               conversion_pct,yield_pct,waste_pct,remark
                               ) VALUES (?,?,?,?,?,?,?,0,0,0,0,?,0,0,?, ?,?,0,0,?,?,?)
                               ON CONFLICT(work_date,shift,machine) DO UPDATE SET
                               production_ton=excluded.production_ton,target_ton=excluded.target_ton,
                               waste_ton=excluded.waste_ton,breakdown_hours=excluded.breakdown_hours,
                               target_type=excluded.target_type,
                               material_available_ton=excluded.material_available_ton,
                               material_processed_ton=excluded.material_processed_ton,
                               good_output_ton=excluded.good_output_ton,
                               yield_pct=excluded.yield_pct,waste_pct=excluded.waste_pct,
                               remark=excluded.remark""",
                            (
                                pdate.isoformat(),shift,machine,good_output,shift_target,waste_ton,
                                breakdown_hours,"FIXED_TON",paper_consumed,paper_consumed,good_output,
                                yield_pct,waste_pct,_save_remark
                            )
                        )
                        record_audit_event(
                            _current_user["username"], "PRODUCTION_SAVE", "Operations",
                            "Production", f"{pdate.isoformat()}|{shift}|{machine}",
                            (
                                f"Type=FIXED_TON; PaperConsumed={paper_consumed:.2f}; GoodOutput={good_output:.2f}; "
                                f"Target={shift_target:.2f}; Achievement={achievement:.2f}%; Waste={waste_ton:.2f}; "
                                f"Yield={yield_pct:.2f}%; WastePct={waste_pct:.2f}%; "
                                f"MaterialVariance={material_variance:.2f}; Breakdown={breakdown_hours:.2f}"
                            )
                        )
                        st.success("Corrugation production entry saved successfully.")
                        st.rerun()
'''

if old not in s:
    raise RuntimeError("Fixed-ton Corrugation block anchor not found")
s=s.replace(old,new,1)

p.write_text(s, encoding="utf-8")
print("Applied V11.7 Corrugation material-balance production entry")
