from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V11.2 MIXED DIVISION ATTENDANCE HANDLING"
if MARK in s:
    print("V11.2 mixed-division attendance handling already applied")
    raise SystemExit(0)

old = '''                        # Block when the file looks structurally assigned to another division.
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
'''

new = '''                        # V11.2 MIXED DIVISION ATTENDANCE HANDLING
                        # If Employee Master confirms the selected division for the clear
                        # majority of known active IDs, treat the minority mismatch as an HR
                        # Review exception instead of blocking the entire file. This handles
                        # transferred/mis-mapped employees safely.
                        _v112_selected_supported = bool(
                            _v110_suggested
                            and _v110_suggested == actual
                            and _v110_suggested_count >= 2
                            and _v110_suggested_pct >= 60.0
                        )
                        _v112_strong_other_division = bool(
                            _v110_suggested
                            and _v110_suggested != actual
                            and _v110_suggested_count >= 2
                            and _v110_suggested_pct >= 60.0
                        )
                        _v112_large_unresolved_mix = bool(
                            not _v112_selected_supported
                            and not _v112_strong_other_division
                            and len(_v110_mismatch_ids) >= 3
                            and _v110_mismatch_rows >= 20
                            and _v110_mismatch_pct >= 50.0
                        )

                        division_guard_block = bool(
                            _v112_strong_other_division or _v112_large_unresolved_mix
                        )
'''

if old not in s:
    raise RuntimeError("V11.0 division guard logic anchor not found")
s = s.replace(old, new, 1)

old_warn = '''                        else:
                            st.warning(
                                f"{_v110_mismatch_rows:,} limited division-mismatch row(s) detected. "
                                "These will be routed to HR Review for HR verification: "
                                + " | ".join(precheck["division_mismatches"][:12])
                            )
'''

new_warn = '''                        else:
                            if _v112_selected_supported:
                                st.warning(
                                    f"⚠️ **Mixed-division attendance accepted for {actual}.** "
                                    f"Employee Master confirms {_v110_suggested_count} employee(s) "
                                    f"({_v110_suggested_pct:.1f}% of known active IDs) belong to **{actual}**. "
                                    f"The {_v110_mismatch_rows:,} row(s) for {len(_v110_mismatch_ids):,} "
                                    "employee(s) mapped to another division will be imported only as "
                                    "**HR Review** for HR verification. The rest of the file can be saved normally."
                                )
                                st.caption(
                                    "Employees requiring division review: "
                                    + ", ".join(_v110_mismatch_ids[:20])
                                )
                            else:
                                st.warning(
                                    f"{_v110_mismatch_rows:,} limited division-mismatch row(s) detected. "
                                    "These will be routed to HR Review for HR verification: "
                                    + " | ".join(precheck["division_mismatches"][:12])
                                )
'''

if old_warn not in s:
    raise RuntimeError("Division warning anchor not found")
s = s.replace(old_warn, new_warn, 1)

p.write_text(s, encoding="utf-8")
print("Applied V11.2 mixed-division attendance handling")
