from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

MARK = "# V11.1 EXPECTED DIVISION AUTHORITATIVE"
if MARK in s:
    print("V11.1 expected-division fix already applied")
    raise SystemExit(0)

old = '''                    actual = detected or expected
                    if detected:
                        st.caption(f"Detected division: **{detected}**")
                        if detected != expected:
                            st.warning(
                                f"You selected **{expected}**, but the file indicates **{detected}**. "
                                "The detected division will be used."
                            )
'''

new = '''                    # V11.1 EXPECTED DIVISION AUTHORITATIVE
                    # The HR-selected Expected Division is authoritative for the import.
                    # File-name / workbook detection is advisory only. The Employee Master
                    # safety guard below independently blocks a genuinely wrong selection.
                    actual = expected
                    if detected:
                        st.caption(f"File label/detection suggests: **{detected}**")
                        if detected != expected:
                            st.info(
                                f"You selected **{expected}**, while the file label/detection suggests **{detected}**. "
                                f"The preview will use **{expected}** and verify every Employee ID against Employee Master. "
                                "If the selected division is wrong, the safety guard will block the import."
                            )
'''

if old not in s:
    raise RuntimeError("Attendance detected-division override anchor not found")
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("Applied V11.1 expected division authoritative fix")
