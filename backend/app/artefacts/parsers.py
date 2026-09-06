from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass

from app.ai.guard import normalise_text

ALLOWED: dict[str, tuple[str, ...]] = {
    # extension -> acceptable declared MIME types
    "pdf": ("application/pdf",),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"),
    "txt": ("text/plain", "application/octet-stream"),
    "md": ("text/markdown", "text/plain", "application/octet-stream"),
    "csv": ("text/csv", "text/plain", "application/octet-stream"),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"),
}

CANONICAL_MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "md": "text/markdown",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

TABULAR_EXTS = {"csv", "xlsx"}


class UnsupportedFile(Exception):
    pass


class NoTextExtracted(Exception):
    pass


def sniff_extension(filename: str, head: bytes) -> str:
    """Determine file type from magic bytes first, falling back to extension for plain text."""
    ext = (filename.rsplit(".", 1)[-1].lower() if "." in filename else "")
    if head.startswith(b"%PDF-"):
        return "pdf"
    if head.startswith(b"PK\x03\x04") and ext == "docx":
        return "docx"
    if head.startswith(b"PK\x03\x04") and ext == "xlsx":
        return "xlsx"
    if ext in ("txt", "md", "csv"):
        if b"\x00" in head[:512]:
            raise UnsupportedFile("Binary content in a text file")
        return ext
    raise UnsupportedFile(f"Unsupported file type '{ext or 'unknown'}'")


def extract_text(ext: str, data: bytes) -> str:
    if ext == "pdf":
        text = _pdf_text(data)
    elif ext == "docx":
        text = _docx_text(data)
    elif ext == "xlsx":
        text = _xlsx_csv(data)
    else:
        text = _decode_text(data)
    text = normalise_text(text)
    if len(text) < 20:
        raise NoTextExtracted("No extractable text (scanned/image document?)")
    return text


def _xlsx_csv(data: bytes) -> str:
    """First worksheet -> CSV text, so marks sheets share one tabular parser."""
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise UnsupportedFile("XLSX support is not installed on this server; upload CSV") from exc
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise UnsupportedFile("Corrupted or unreadable XLSX") from exc
    ws = wb.worksheets[0]
    buf = io.StringIO()
    w = csv.writer(buf)
    for row in ws.iter_rows(values_only=True):
        w.writerow(["" if v is None else v for v in row])
    return buf.getvalue()


def _decode_text(data: bytes) -> str:
    for enc in ("utf-8", "utf-16", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:  # noqa: BLE001
                raise UnsupportedFile("Encrypted PDF") from exc
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except PyPdfError as exc:
        raise UnsupportedFile("Corrupted or unreadable PDF") from exc


def _docx_text(data: bytes) -> str:
    import docx

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001 - python-docx raises assorted zip/xml errors
        raise UnsupportedFile("Corrupted or unreadable DOCX") from exc
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text for c in row.cells))
    return "\n".join(parts)


def detect_lang(text: str) -> str:
    bn = len(re.findall(r"[\u0980-\u09FF]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if bn == 0 and latin == 0:
        return "unknown"
    if bn == 0:
        return "en"
    if latin == 0:
        return "bn"
    return "mixed" if min(bn, latin) / max(bn, latin) > 0.15 else ("bn" if bn > latin else "en")


# ---------------------------------------------------------------------------
# Deterministic heuristic splitters (used by the mock provider and as evidence anchors)
# ---------------------------------------------------------------------------

_Q_START = re.compile(
    r"^\s*(?:Q(?:uestion)?\.?\s*)?(\d{1,2})\s*[\.\)]?\s*(?:\(?([a-h])\)?[\.\)]?)?\s+(?=\S)", re.IGNORECASE
)
_SUBPART_START = re.compile(r"^\s*\(?([a-h])\)\s+(?=\S)", re.IGNORECASE)
_MARKS = re.compile(r"[\[\(]\s*(\d{1,3}(?:\.\d+)?)\s*(?:marks?|m)?\s*[\]\)]\s*$|(\d{1,3}(?:\.\d+)?)\s*marks?\s*$", re.IGNORECASE)


@dataclass
class HeuristicQuestion:
    number: str
    text: str
    marks: float | None


def split_questions_heuristic(text: str) -> list[dict]:
    """Split exam text into numbered questions; sub-parts inherit the current main number."""
    items: list[HeuristicQuestion] = []
    current_main = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _Q_START.match(line)
        sub = _SUBPART_START.match(line) if not m else None
        if m:
            current_main = m.group(1)
            part = m.group(2)
            number = f"{current_main}({part.lower()})" if part else current_main
            body = line[m.end():]
        elif sub and current_main:
            number = f"{current_main}({sub.group(1).lower()})"
            body = line[sub.end():]
        elif items:
            items[-1].text = f"{items[-1].text} {line}".strip()
            _pull_marks(items[-1])
            continue
        else:
            continue
        q = HeuristicQuestion(number=number, text=body.strip(), marks=None)
        _pull_marks(q)
        items.append(q)
    # a bare main number that only introduces sub-parts (e.g. "3. Answer both:") is dropped
    numbers = [q.number for q in items]
    cleaned = [
        q for q in items
        if not ("(" not in q.number and any(n.startswith(f"{q.number}(") for n in numbers) and q.marks is None)
    ]
    return [{"number": q.number, "text": q.text, "marks": q.marks if q.marks is not None else 0.0} for q in cleaned if q.text]


def _pull_marks(q: HeuristicQuestion) -> None:
    m = _MARKS.search(q.text)
    if m:
        q.marks = float(m.group(1) or m.group(2))
        q.text = q.text[: m.start()].rstrip(" -–:")


_TOPIC_LINE = re.compile(r"^\s*(?:week\s*\d+\s*[:\-.]?\s*|\d{1,2}\s*[\.\)]\s*|[-•*]\s*)(.+)$", re.IGNORECASE)


def split_topics_heuristic(text: str) -> list[dict]:
    topics: list[dict] = []
    for raw in text.splitlines():
        line = raw.strip()
        if len(line) < 4:
            continue
        m = _TOPIC_LINE.match(line)
        title = (m.group(1) if m else line).strip(" .;")
        if len(title) < 2 or len(title) > 200:
            continue
        topics.append({"code": f"T-{len(topics) + 1:02d}", "title": title})
    return topics[:60]


# ---------------------------------------------------------------------------
# Marks sheet (CSV text). Header: <student id> [, roll, name] , <question columns...> [, total]
# Question header forms: "1(a)", "Q1a", "1(a) (CO1/5)", "Q2 [10]", "3 (CO4/10)".
# ---------------------------------------------------------------------------

_ID_HEADERS = ("student", "id", "roll", "reg", "sl", "no", "#")
_SKIP_HEADERS = ("name", "roll", "reg", "email", "section", "total", "grade", "percentage", "remarks")
_COL_META = re.compile(r"\(\s*(?:(CO\s*\d{1,2})\s*/\s*)?(\d{1,3}(?:\.\d+)?)\s*\)|\[\s*(\d{1,3}(?:\.\d+)?)\s*\]", re.IGNORECASE)


def normalize_qnum(raw: str) -> str:
    """'Q1 (a)', '1a', '1.a', 'Q1(A)' -> '1(a)'; 'Q5' -> '5'. Port of database normalize_qnum()."""
    s = re.sub(r"^\s*q(?:uestion)?\.?\s*", "", raw.strip(), flags=re.IGNORECASE)
    m = re.match(r"^(\d{1,2})\s*[\.\-\s]?\s*\(?\s*([a-h])?\s*\)?\s*(?:[\.\)]|$)", s, flags=re.IGNORECASE)
    if not m:
        return "".join(s.split())
    return f"{m.group(1)}({m.group(2).lower()})" if m.group(2) else m.group(1)


def anonymise_student(raw: str) -> str:
    """Keep already-anonymous ids (S-001, 2101...) as-is; hash anything that looks like a name (SEC-007)."""
    s = raw.strip()
    if re.fullmatch(r"[A-Za-z]{0,3}[-_ ]?\d{1,12}", s):
        return s
    return "S-" + hashlib.sha256(s.lower().encode()).hexdigest()[:8]


def parse_marks_csv(text: str) -> dict:
    """Returns {columns:[{number,max_marks,co_code}], rows:[{student_anon_id, scores{number:score}}], warnings:[...]}."""
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [r for r in reader if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise NoTextExtracted("Marks sheet needs a header row and at least one student row")
    header = [h.strip() for h in rows[0]]
    warnings: list[str] = []
    id_idx = 0
    for i, h in enumerate(header):
        if any(k in h.lower() for k in _ID_HEADERS) and not any(k in h.lower() for k in ("total", "name")):
            id_idx = i
            break
    columns: list[dict] = []
    col_idx: list[int] = []
    for i, h in enumerate(header):
        if i == id_idx or not h:
            continue
        if any(k in h.lower() for k in _SKIP_HEADERS):
            continue
        meta = _COL_META.search(h)
        label = _COL_META.sub("", h).strip(" :-")
        number = normalize_qnum(label) if label else f"C{len(columns) + 1}"
        max_marks = float(meta.group(2) or meta.group(3)) if meta and (meta.group(2) or meta.group(3)) else None
        co_code = "".join(meta.group(1).upper().split()) if meta and meta.group(1) else None
        if any(c["number"] == number for c in columns):
            warnings.append(f"Duplicate column '{h}' ignored")
            continue
        columns.append({"number": number, "max_marks": max_marks, "co_code": co_code})
        col_idx.append(i)
    if not columns:
        raise NoTextExtracted("No question columns found in the marks sheet header")
    out_rows: list[dict] = []
    seen: set[str] = set()
    for r in rows[1:]:
        if id_idx >= len(r) or not r[id_idx].strip():
            continue
        sid = anonymise_student(r[id_idx])
        if sid in seen:
            warnings.append(f"Duplicate student id '{sid}' — later row ignored")
            continue
        seen.add(sid)
        scores: dict[str, float] = {}
        for c, i in zip(columns, col_idx, strict=True):
            cell = r[i].strip() if i < len(r) else ""
            if cell in ("", "-", "AB", "ab", "A", "NA", "n/a"):
                continue
            try:
                scores[c["number"]] = float(cell.replace(",", "."))
            except ValueError:
                warnings.append(f"Non-numeric score '{cell}' for {sid} / {c['number']} ignored")
        out_rows.append({"student_anon_id": sid, "scores": scores})
    if not out_rows:
        raise NoTextExtracted("No student rows found in the marks sheet")
    for c in columns:  # infer max from data when the header did not declare it
        if c["max_marks"] is None:
            observed = [r["scores"][c["number"]] for r in out_rows if c["number"] in r["scores"]]
            c["max_marks"] = max(observed) if observed else 0.0
            warnings.append(f"Column '{c['number']}': max marks not declared, using highest observed score {c['max_marks']:g}")
    return {"columns": columns, "rows": out_rows, "warnings": warnings}


# ---------------------------------------------------------------------------
# Rubric (plain text). One criterion per block:
#   R1 (4 marks): Anomaly identification — All three anomalies named...
#   4: All three anomalies with examples.   <- optional level lines "score: descriptor"
# ---------------------------------------------------------------------------

_CRIT_START = re.compile(
    r"^\s*(?:criterion\s+(\d{1,2})|([A-Z]{1,3}\s*-?\s*\d{1,2})\b|(\d{1,2})\s*[\.\)])\s*"
    r"(?:[\[\(]\s*(?:max\s*)?(\d{1,3}(?:\.\d+)?)\s*(?:marks?|pts?|points?)?\s*[\]\)])?\s*[:\-–]?\s*(.+)$",
    re.IGNORECASE,
)
# "4: descriptor" / "Band 3 - descriptor" are level lines; "4. text" / "R1 text" are criteria.
_LEVEL_LINE = re.compile(r"^\s*(?:band|level|score)?\s*(\d{1,3}(?:\.\d+)?)\s*(?:marks?|pts?)?\s*[:=–-]\s*(.+)$", re.IGNORECASE)
_TRAILING_MAX = re.compile(r"[\[\(]\s*(?:max\s*)?(\d{1,3}(?:\.\d+)?)\s*(?:marks?|pts?|points?)?\s*[\]\)]\s*$", re.IGNORECASE)


def split_rubric_heuristic(text: str) -> list[dict]:
    criteria: list[dict] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _CRIT_START.match(line)
        lvl = _LEVEL_LINE.match(line)
        if lvl and criteria and (not m or (m.group(3) and not re.match(r"^\s*\d{1,2}\s*[\.\)]", line))):
            criteria[-1]["levels"].append({"label": f"{float(lvl.group(1)):g}", "score": float(lvl.group(1)), "descriptor": lvl.group(2).strip()})
            continue
        if m:
            code = "".join((m.group(2) or f"R{m.group(1) or m.group(3)}").upper().split())
            body = m.group(5).strip()
            mx = float(m.group(4)) if m.group(4) else None
            t = _TRAILING_MAX.search(body)
            if t:
                mx = mx or float(t.group(1))
                body = body[: t.start()].rstrip(" -–:")
            if not body:
                continue
            criteria.append({"code": code, "text": body[:1000], "max_score": mx, "levels": []})
        elif criteria:
            criteria[-1]["text"] = f"{criteria[-1]['text']} {line}".strip()[:1000]
    for c in criteria:
        if c["max_score"] is None:
            c["max_score"] = max((lv["score"] for lv in c["levels"]), default=0.0)
        c["levels"].sort(key=lambda lv: -lv["score"])
    return [c for c in criteria if c["max_score"] and c["max_score"] > 0][:40]


# ---------------------------------------------------------------------------
# Answer set (plain text). Blocks separated by a "Student:" line:
#   Student: S-004        Question: 6
#   <answer text ... multiple lines>
#   Grader A: R1=4, R2=3, R3=5
#   Grader B: R1=3 R2=3 R3=2
# ---------------------------------------------------------------------------

_ANS_STUDENT = re.compile(r"^\s*(?:student|script|answer)\s*(?:id)?\s*[:#-]\s*(\S+)(?:\s+(?:question|q)\s*[:#-]?\s*(\S+))?", re.IGNORECASE)
_ANS_GRADER = re.compile(r"^\s*(?:grader|marker|examiner)\s*[:#-]?\s*([A-Za-z0-9 _.-]{1,40}?)\s*[:\-–]\s*(.+)$", re.IGNORECASE)
_ANS_SCORE = re.compile(r"([A-Za-z]{1,3}\s*-?\s*\d{1,2}|\d{1,2})\s*[=:]\s*(\d{1,3}(?:\.\d+)?)")
_ANS_QUESTION = re.compile(r"^\s*question\s*[:#-]?\s*(\S+)", re.IGNORECASE)


def split_answers_heuristic(text: str) -> list[dict]:
    answers: list[dict] = []
    cur: dict | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        ms = _ANS_STUDENT.match(line)
        if ms and not _ANS_GRADER.match(line):
            cur = {"student_anon_id": anonymise_student(ms.group(1)), "question_ref": ms.group(2), "text": "", "grader_scores": []}
            answers.append(cur)
            continue
        if cur is None:
            continue
        mq = _ANS_QUESTION.match(line)
        if mq and not cur["text"]:
            cur["question_ref"] = mq.group(1)
            continue
        mg = _ANS_GRADER.match(line)
        if mg:
            grader = " ".join(mg.group(1).split())
            for code, score in _ANS_SCORE.findall(mg.group(2)):
                cur["grader_scores"].append({"grader_label": grader, "criterion_code": "".join(code.upper().split()), "score": float(score)})
            continue
        cur["text"] = f"{cur['text']} {line}".strip()
    return [a for a in answers if a["text"]][:200]
