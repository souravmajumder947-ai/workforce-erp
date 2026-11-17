# HR & Production Cost Management System

Focus:
- Employee Master with monthly salary
- Attendance and overtime
- Employee-to-machine allocation
- Production entry
- Labour cost and OT cost
- Cost per ton
- Machine manpower gap and efficiency
- Shift A and Shift B
- CSV reports

## Local run

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Streamlit Cloud
Upload `app.py` and `requirements.txt` to GitHub, then deploy `app.py` from Streamlit Community Cloud.

SQLite is suitable for testing and a single-user demo. Use PostgreSQL before storing permanent multi-user company data.

## JARVIS ERP questions

JARVIS reads existing ERP records without an external AI API. Daily MIS and employee questions are available according to the account's existing permissions. It covers Greater Noida Plant and Sector 63 Head Office.
