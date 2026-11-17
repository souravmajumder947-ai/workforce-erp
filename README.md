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

## JARVIS public questions

In the existing Streamlit app secrets, add `OPENAI_API_KEY` as a top-level TOML value. Keep the existing PostgreSQL settings. A local installation can also supply the key through the environment. The optional `JARVIS_OPENAI_MODEL` environment variable selects a Responses API model with web search support.

Owners, Admins, and Managers can open JARVIS from the sidebar. The public question tab sends the submitted text to OpenAI. Internal ERP report and employee tabs use their existing permissions, run independently, and do not send company records to the public question service.
