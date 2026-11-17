"""Extract and record warning letters within the authenticated HR workspace."""
from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from xml.etree import ElementTree
from zipfile import ZipFile

from PIL import Image, ImageOps
from pypdf import PdfReader
import streamlit as st


MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 8
MAX_OCR_PAGES = 3
MAX_TEXT = 45_000
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

LABELS = {
    "employee_id": r"(?:employee|emp\.?)[ \t]*(?:id|code|no\.?|number)",
    "employee_name": r"(?:employee|emp\.?)\s+name",
    "issue_date": r"(?:date\s+of\s+issue|issu(?:e|ed)\s+date|letter\s+date|dated?|issued\s+on)",
    "incident_date": r"(?:incident\s+date|date\s+of\s+(?:incident|misconduct))",
    "subject": r"(?:subject|sub\.?)",
    "reference": r"(?:ref(?:erence)?(?:\s+(?:no\.?|number))?|letter\s+no\.?)",
    "warning_type": r"(?:warning\s+(?:type|level)|type\s+of\s+warning)",
    "reason": r"(?:reason(?:\s+for\s+(?:the\s+)?warning)?|incident\s+details|description(?:\s+of\s+(?:the\s+)?incident)?|allegation)",
    "required_action": r"(?:corrective\s+action(?:\s+required)?|action\s+required|required\s+action|expected\s+improvement)",
}
FIELD_PATTERN = re.compile(
    r"^[ \t]*(?:" + "|".join(f"(?P<{key}>{label})" for key, label in LABELS.items())
    + r")[ \t]*[:：–-][ \t]*(?P<value>[^\n]*)$",
    re.IGNORECASE | re.MULTILINE,
)
DATE_TOKEN = re.compile(
    r"\b(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}"
    r"|\d{1,2}(?:st|nd|rd|th)?[\s-]+[A-Za-z]{3,9}[\s,-]+\d{4})\b", re.IGNORECASE,
)
DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y", "%d %B %Y", "%d %b %Y")
SALUTATION = re.compile(r"(?im)^\s*(?:dear\s+[^\n]+|to\s*:\s*[^\n]+)[ \t]*,?[ \t]*$")
CLOSING = re.compile(
    r"(?im)^\s*(?:yours\s+(?:faithfully|sincerely|truly)|sincerely|regards|for reliable packaging|"
    r"authorized signatory|authorised signatory|acknowledg(?:e)?ment)\b"
)


@dataclass(frozen=True)
class Letter:
    employee_ids: tuple[str, ...]
    employee_name: str
    issue_date: date | None
    incident_date: date | None
    subject: str
    reference: str
    warning_type: str
    reason: str
    required_action: str


def _parse_date(text):
    match = DATE_TOKEN.search(text)
    if not match:
        return None
    value = re.sub(r"(?<=\d)(?:st|nd|rd|th)\b", "", match.group(), flags=re.IGNORECASE)
    if re.search(r"[A-Za-z]", value):
        value = re.sub(r"[\s,-]+", " ", value)
    else:
        value = re.sub(r"[/.]", "-", value)
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    return None


def _run_ocr(command):
    try:
        return subprocess.run(command, capture_output=True, check=True, timeout=12).stdout.decode("utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise ValueError("Scanned letters need OCR support. Use a text PDF or DOCX until OCR is installed.") from exc
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("The scan could not be read. Upload a clearer scan or a text PDF or DOCX.") from exc


def _pdf_text(payload):
    reader = PdfReader(BytesIO(payload))
    if reader.is_encrypted or not 1 <= len(reader.pages) <= MAX_PAGES:
        raise ValueError("Upload an unlocked PDF with one to eight pages.")
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    scan_indexes = [index for index, page in enumerate(pages) if sum(c.isalpha() for c in page) < 30]
    if len(scan_indexes) > MAX_OCR_PAGES:
        raise ValueError("Upload up to three scanned pages per letter, or use a searchable PDF.")
    if scan_indexes:
        with TemporaryDirectory() as folder:
            source = Path(folder) / "letter.pdf"
            source.write_bytes(payload)
            for index in scan_indexes:
                page = str(index + 1)
                image = Path(folder) / "page"
                _run_ocr(["pdftoppm", "-f", page, "-l", page, "-scale-to", "2500", "-png", "-singlefile", str(source), str(image)])
                pages[index] = _run_ocr(["tesseract", str(image.with_suffix(".png")), "stdout", "-l", "eng"])
    return "\n".join(pages)


def _docx_text(payload):
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(BytesIO(payload)) as archive:
        document = archive.getinfo("word/document.xml")
        if document.file_size > 2 * 1024 * 1024:
            raise ValueError("The Word letter contains too much text to process.")
        root = ElementTree.fromstring(archive.read(document))
    return "\n".join(
        "".join(node.text or "" for node in paragraph.findall(".//w:t", ns))
        for paragraph in root.findall(".//w:p", ns)
    )


def _image_text(payload, suffix):
    with TemporaryDirectory() as folder, Image.open(BytesIO(payload)) as image:
        expected_format = "PNG" if suffix == ".png" else "JPEG"
        if image.format != expected_format or image.width * image.height > 20_000_000:
            raise ValueError("Upload a valid PNG or JPEG scan under 20 megapixels.")
        page = ImageOps.exif_transpose(image).convert("RGB")
        page.thumbnail((2800, 2800))
        source = Path(folder) / "scan.png"
        page.save(source)
        return _run_ocr(["tesseract", str(source), "stdout", "-l", "eng"])


def extract_text(payload, suffix):
    if not 0 < len(payload) <= MAX_BYTES:
        raise ValueError("Choose a file under 8 MB.")
    if suffix == ".pdf":
        if not payload.startswith(b"%PDF-"):
            raise ValueError("Choose a valid PDF.")
        text = _pdf_text(payload)
    elif suffix == ".docx":
        text = _docx_text(payload)
    elif suffix in {".png", ".jpg", ".jpeg"}:
        text = _image_text(payload, suffix)
    else:
        raise ValueError("Choose a PDF, DOCX, PNG or JPEG.")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "").strip()
    if len(text) > MAX_TEXT:
        raise ValueError("Choose a warning letter with fewer than 45,000 text characters.")
    return text


def parse_letter(text):
    matches = list(FIELD_PATTERN.finditer(text))
    fields = {}
    employee_ids = []
    for index, match in enumerate(matches):
        field = next(key for key in LABELS if match.group(key) is not None)
        value = match.group("value").strip()
        if field in {"reason", "required_action"}:
            stop = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            continuation = CLOSING.split(text[match.end():stop], maxsplit=1)[0].strip()
            value = "\n".join(part for part in (value, continuation) if part)
        if field == "employee_id":
            code = re.match(r"[A-Za-z0-9][A-Za-z0-9_./-]*", value)
            if code:
                employee_ids.append(code.group().rstrip("./-"))
        elif value:
            fields.setdefault(field, value)

    subject = fields.get("subject", "")
    if not subject:
        heading = re.search(r"(?im)^\s*((?:(?:first|second|final|written|verbal|formal)\s+)?warning\s+(?:letter|notice)\b[^\n]*)", text)
        subject = heading.group(1).strip() if heading else "Warning letter"
    warning_type = fields.get("warning_type", "")
    if not warning_type:
        level = re.search(r"\b(first|second|final|written|verbal)\s+warning\b", subject, re.IGNORECASE)
        warning_type = level.group(1).title() + " warning" if level else ""
    reason = fields.get("reason", "")
    if not reason:
        salutation = SALUTATION.search(text)
        if salutation:
            body = CLOSING.split(text[salutation.end():], maxsplit=1)[0].strip()
            reason = body.split("\n\n", 1)[0].strip()[:1500]
    return Letter(
        tuple(dict.fromkeys(employee_ids)), fields.get("employee_name", ""),
        _parse_date(fields.get("issue_date", "")), _parse_date(fields.get("incident_date", "")),
        subject, fields.get("reference", ""), warning_type, reason, fields.get("required_action", ""),
    )


def save_letter(get_conn, employee_id, actor, filename, mime, payload, details):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO employee_warning_letters
                   (employee_id, issue_date, incident_date, subject, warning_type, reference_no, reason,
                    required_action, filename, mime_type, attachment, content_hash, recorded_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (content_hash) DO NOTHING
                   RETURNING warning_id""",
                (employee_id, *details, filename, mime, payload, sha256(payload).hexdigest(), actor),
            )
            saved = cur.fetchone()
            if saved is None:
                return False
            cur.execute(
                """INSERT INTO audit_log(actor, action, module, entity_type, entity_id, details)
                   VALUES (%s,'CREATE','Employee 360','Warning Letter',%s,'Warning letter recorded')""",
                (actor, str(saved[0])),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def render_warning_letters(employee, actor, role, can_edit_hr, read_df, get_conn):
    if not can_edit_hr(role):
        return
    employee_id = str(employee["employee_id"])
    st.subheader("Warning letters")
    if st.session_state.pop(f"warning_saved_{employee_id}", False):
        st.success("Warning letter saved to this employee profile.")
    history = read_df(
        """SELECT warning_id,issue_date,incident_date,subject,warning_type,reference_no,
                  reason,required_action,filename,recorded_by,recorded_at
           FROM employee_warning_letters WHERE employee_id=?
           ORDER BY issue_date DESC, warning_id DESC""",
        (employee_id,),
    )
    if history.empty:
        st.info("No warning letters recorded.")
    else:
        st.dataframe(history[["issue_date", "subject", "warning_type", "reference_no", "recorded_by"]].rename(columns={
            "issue_date": "Issue date", "subject": "Subject", "warning_type": "Warning type",
            "reference_no": "Reference", "recorded_by": "Recorded by",
        }), hide_index=True, width="stretch")
        records = {row.warning_id: row for row in history.itertuples(index=False)}
        selected = st.selectbox(
            "View a warning letter", list(records), index=None,
            format_func=lambda key: f"{records[key].issue_date:%d %b %Y} · {records[key].subject}",
            key=f"warning_record_{employee_id}",
        )
        if selected is not None:
            record = records[selected]
            if record.incident_date:
                st.text(f"Incident date: {record.incident_date:%d %b %Y}")
            st.text(f"Reason: {record.reason}")
            if record.required_action:
                st.text(f"Required action: {record.required_action}")
            document = read_df(
                "SELECT attachment,mime_type FROM employee_warning_letters WHERE employee_id=? AND warning_id=?",
                (employee_id, int(selected)),
            )
            if not document.empty:
                st.download_button("Download original letter", bytes(document.iloc[0].attachment),
                                   file_name=record.filename, mime=document.iloc[0].mime_type,
                                   on_click="ignore")

    upload = st.file_uploader(
        "Upload warning letter", type=["pdf", "docx", "png", "jpg", "jpeg"],
        key=f"warning_upload_{actor}_{employee_id}", help="Use a file under 8 MB. English scans are read with OCR.",
    )
    if upload is None:
        return
    payload = upload.getvalue()
    if len(payload) > MAX_BYTES:
        st.error("Choose a file under 8 MB.")
        return
    digest = sha256(payload).hexdigest()
    if not read_df("SELECT warning_id FROM employee_warning_letters WHERE content_hash=?", (digest,)).empty:
        st.info("This exact file is already recorded in Employee 360.")
        return
    suffix = Path(upload.name).suffix.lower()
    extraction_key = (actor, employee_id, digest, suffix)
    text_state = st.session_state.get("warning_letter_extraction")
    if text_state is None or text_state[0] != extraction_key:
        try:
            with st.spinner("Reading warning letter…"):
                text = extract_text(payload, suffix)
            text_state = (extraction_key, text, None)
        except ValueError as exc:
            text_state = (extraction_key, "", str(exc))
        except Exception:
            text_state = (extraction_key, "", "Could not read the file. Open it and upload a fresh copy.")
        st.session_state["warning_letter_extraction"] = text_state
    _, text, error = text_state
    if error:
        st.error(error)
        return
    extracted = parse_letter(text)
    if any(found.casefold() != employee_id.casefold() for found in extracted.employee_ids):
        st.error("An employee ID on this letter differs from this profile. Open the correct employee profile before saving.")
        return
    profile_name = str(employee.get("employee_name") or "")
    if extracted.employee_name and " ".join(extracted.employee_name.casefold().split()) != " ".join(profile_name.casefold().split()):
        st.warning(f"The letter shows employee name \"{extracted.employee_name}\". Check it against this profile.")
    if not extracted.employee_ids:
        st.info("No employee ID was detected. Verify the original letter belongs to this profile.")
    if text:
        with st.expander("Text read from the letter"):
            st.text(text)
    else:
        st.warning("No text was detected. Review the original file and enter the details below.")
    st.caption(f"Review the details for {profile_name} ({employee_id}) before saving.")
    with st.form(f"warning_letter_{actor}_{employee_id}_{digest}"):
        first, second = st.columns(2)
        issue_date = first.date_input("Issue date", value=extracted.issue_date)
        incident_date = second.date_input("Incident date (optional)", value=extracted.incident_date)
        subject = st.text_input("Subject", value=extracted.subject[:250], max_chars=250)
        warning_type = first.text_input("Warning type (optional)", value=extracted.warning_type[:100], max_chars=100)
        reference = second.text_input("Reference number (optional)", value=extracted.reference[:100], max_chars=100)
        reason = st.text_area("Reason stated in the letter", value=extracted.reason[:6000], max_chars=6000)
        action = st.text_area("Required action (optional)", value=extracted.required_action[:6000], max_chars=6000)
        confirmed = st.checkbox("I verified the employee and the letter details")
        submitted = st.form_submit_button("Save warning letter", type="primary")
    if not submitted:
        return
    if not confirmed or not issue_date or not subject.strip() or not reason.strip():
        st.error("Enter the issue date, subject and reason, then confirm the employee and the details.")
        return
    try:
        filename = Path(upload.name.replace("\\", "/")).name
        saved = save_letter(
            get_conn, employee_id, actor, filename, MIME_TYPES[suffix], payload,
            (issue_date, incident_date, subject.strip(), warning_type.strip(), reference.strip(), reason.strip(), action.strip()),
        )
    except Exception:
        st.error("The warning letter could not be saved. Try again.")
        return
    if saved:
        st.session_state.pop("warning_letter_extraction", None)
        st.session_state[f"warning_saved_{employee_id}"] = True
        st.rerun()
    else:
        st.info("This exact file was already recorded.")
