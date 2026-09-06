from __future__ import annotations

import io
import uuid

from docx import Document
from pypdf import PdfWriter

from app.ai.providers.base import ProviderError
from tests.conftest import DRAFT_PAPER, OUTCOMES, make_course, upload_text, wait_until_done


def _pdf_bytes(text: str | None) -> bytes:
    w = PdfWriter()
    w.add_blank_page(width=300, height=300)  # blank page = "scanned" PDF with no text layer
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def _docx_bytes(text: str) -> bytes:
    d = Document()
    for line in text.splitlines():
        d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


async def test_upload_txt_and_extract_questions(client, user_a):
    course = await make_course(client, user_a)
    r = await client.post(
        f"/courses/{course['id']}/artefacts",
        data={"kind": "question_paper", "label": "Draft", "declared_total_marks": "60"},
        files={"file": ("draft.txt", DRAFT_PAPER.encode(), "text/plain")},
        headers=user_a,
    )
    assert r.status_code == 202 and r.json()["status"] == "extracting"
    aid = r.json()["id"]
    await wait_until_done()
    art = (await client.get(f"/artefacts/{aid}", headers=user_a)).json()
    assert art["status"] == "done" and art["counts"]["questions"] == 9 and art["lang"] == "en"
    assert art["mime"] == "text/plain" and art["declared_total_marks"] == 60
    qs = (await client.get(f"/artefacts/{aid}/questions", headers=user_a)).json()
    assert [q["number"] for q in qs][:3] == ["1(a)", "1(b)", "2(a)"]
    assert sum(q["marks"] for q in qs) == 58
    text = (await client.get(f"/artefacts/{aid}/text", headers=user_a)).json()
    assert "DRAFT" in text["extracted_text"]
    lst = (await client.get(f"/courses/{course['id']}/artefacts?kind=question_paper&status=done", headers=user_a)).json()
    assert len(lst) == 1


async def test_upload_docx_and_paste_text(client, user_a):
    course = await make_course(client, user_a)
    r = await client.post(
        f"/courses/{course['id']}/artefacts",
        data={"kind": "question_paper", "label": "Docx"},
        files={"file": ("paper.docx", _docx_bytes(DRAFT_PAPER), "application/octet-stream")},
        headers=user_a,
    )
    assert r.status_code == 202, r.text
    await wait_until_done()
    art = (await client.get(f"/artefacts/{r.json()['id']}", headers=user_a)).json()
    assert art["status"] == "done" and art["counts"]["questions"] == 9
    art = await upload_text(client, user_a, course["id"], kind="syllabus", label="Syllabus", text="Week 1: Intro to DBMS\nWeek 2: ER modelling\nWeek 3: SQL")
    assert art["status"] == "done" and art["counts"]["topics"] == 3
    topics = (await client.get(f"/courses/{course['id']}/topics", headers=user_a)).json()
    assert [t["code"] for t in topics] == ["T-01", "T-02", "T-03"] and topics[0]["source_artefact_id"] == art["id"]


async def test_upload_validation_errors(client, user_a):
    course = await make_course(client, user_a)
    url = f"/courses/{course['id']}/artefacts"
    # wrong type (magic bytes) despite .pdf extension
    r = await client.post(url, data={"kind": "question_paper", "label": "x"}, files={"file": ("evil.pdf", b"MZ\x90\x00binary", "application/pdf")}, headers=user_a)
    assert r.status_code == 415 and r.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    r = await client.post(url, data={"kind": "question_paper", "label": "x"}, files={"file": ("a.exe", b"hello", "application/octet-stream")}, headers=user_a)
    assert r.status_code == 415
    # oversized (MAX_UPLOAD_MB=1 in tests)
    r = await client.post(url, data={"kind": "question_paper", "label": "x"}, files={"file": ("big.txt", b"a" * (1024 * 1024 + 1), "text/plain")}, headers=user_a)
    assert r.status_code == 413 and r.json()["error"]["code"] == "FILE_TOO_LARGE"
    # blank pdf -> no text
    r = await client.post(url, data={"kind": "question_paper", "label": "x"}, files={"file": ("scan.pdf", _pdf_bytes(None), "application/pdf")}, headers=user_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "ARTEFACT_NO_TEXT"
    # corrupted pdf
    r = await client.post(url, data={"kind": "question_paper", "label": "x"}, files={"file": ("bad.pdf", b"%PDF-1.4 garbage", "application/pdf")}, headers=user_a)
    assert r.status_code in (415, 422)
    # neither file nor text / both
    r = await client.post(url, data={"kind": "question_paper", "label": "x"}, headers=user_a)
    assert r.status_code == 422
    r = await client.post(url, data={"kind": "question_paper", "label": "x", "text": DRAFT_PAPER}, files={"file": ("a.txt", b"hello world text", "text/plain")}, headers=user_a)
    assert r.status_code == 422
    # unsupported kind in this build
    r = await client.post(url, data={"kind": "marks_sheet", "label": "x", "text": DRAFT_PAPER}, headers=user_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "ARTEFACT_KIND_NOT_SUPPORTED"
    r = await client.post(url, data={"kind": "bogus", "label": "x", "text": DRAFT_PAPER}, headers=user_a)
    assert r.status_code == 422
    r = await client.post(url, data={"kind": "question_paper", "label": "x", "text": "short"}, headers=user_a)
    assert r.status_code == 422 and r.json()["error"]["code"] == "ARTEFACT_NO_TEXT"
    # invalid course
    r = await client.post(f"/courses/{uuid.uuid4()}/artefacts", data={"kind": "question_paper", "label": "x", "text": DRAFT_PAPER}, headers=user_a)
    assert r.status_code == 404


async def test_extraction_failure_marks_artefact_failed_and_faculty_can_fix(client, user_a, mock_provider):
    course = await make_course(client, user_a)
    mock_provider.queue("extract_questions", ProviderError("down"))
    mock_provider.queue("extract_questions", ProviderError("down"))
    r = await client.post(f"/courses/{course['id']}/artefacts", data={"kind": "question_paper", "label": "Draft", "text": DRAFT_PAPER}, headers=user_a)
    aid = r.json()["id"]
    await wait_until_done()
    art = (await client.get(f"/artefacts/{aid}", headers=user_a)).json()
    assert art["status"] == "failed" and "unavailable" in art["error"]
    # faculty enters questions manually -> artefact becomes done
    r = await client.put(f"/artefacts/{aid}/questions", json=[{"number": "1", "text": "Define a transaction and its properties.", "marks": 10}], headers=user_a)
    assert r.status_code == 200 and len(r.json()) == 1
    assert (await client.get(f"/artefacts/{aid}", headers=user_a)).json()["status"] == "done"
    # reextract works again once provider is healthy
    r = await client.post(f"/artefacts/{aid}/reextract", headers=user_a)
    assert r.status_code == 202
    await wait_until_done()
    assert (await client.get(f"/artefacts/{aid}", headers=user_a)).json()["counts"]["questions"] == 9


async def test_questions_confirm_edit_and_co_map(client, user_a, user_b):
    course = await make_course(client, user_a)
    cos = (await client.put(f"/courses/{course['id']}/outcomes", json=OUTCOMES, headers=user_a)).json()
    art = await upload_text(client, user_a, course["id"], kind="question_paper", label="Draft", text=DRAFT_PAPER)
    qs = (await client.get(f"/artefacts/{art['id']}/questions", headers=user_a)).json()
    # edit: fix marks of Q5 from 5 -> 7 and drop Q4(b)
    body = [{"id": q["id"], "number": q["number"], "text": q["text"], "marks": 7 if q["number"] == "5" else q["marks"]} for q in qs if q["number"] != "4(b)"]
    r = await client.put(f"/artefacts/{art['id']}/questions", json=body, headers=user_a)
    assert r.status_code == 200
    numbers = [q["number"] for q in r.json()]
    assert "4(b)" not in numbers and next(q for q in r.json() if q["number"] == "5")["marks"] == 7
    # duplicate numbers rejected
    r = await client.put(f"/artefacts/{art['id']}/questions", json=[{"number": "1", "text": "aaa", "marks": 1}, {"number": "1", "text": "bbb", "marks": 1}], headers=user_a)
    assert r.status_code == 422
    # co-map
    q1 = r.status_code and (await client.get(f"/artefacts/{art['id']}/questions", headers=user_a)).json()[0]
    r = await client.put(f"/artefacts/{art['id']}/questions/co-map", json=[{"question_id": q1["id"], "co_ids": [cos[0]["id"], cos[0]["id"]]}], headers=user_a)
    assert r.status_code == 200 and r.json()[0]["co_ids"] == [cos[0]["id"]]
    r = await client.put(f"/artefacts/{art['id']}/questions/co-map", json=[{"question_id": q1["id"], "co_ids": [str(uuid.uuid4())]}], headers=user_a)
    assert r.status_code == 422
    # deleting a mapped CO -> 409 OUTCOME_IN_USE
    r = await client.put(f"/courses/{course['id']}/outcomes", json=[{"id": c["id"], "code": c["code"], "text": c["text"]} for c in cos[1:]], headers=user_a)
    assert r.status_code == 409 and r.json()["error"]["code"] == "OUTCOME_IN_USE"
    # isolation
    assert (await client.get(f"/artefacts/{art['id']}", headers=user_b)).status_code == 404
    assert (await client.delete(f"/artefacts/{art['id']}", headers=user_b)).status_code == 404
    # delete
    assert (await client.delete(f"/artefacts/{art['id']}", headers=user_a)).status_code == 204
    assert (await client.get(f"/artefacts/{art['id']}", headers=user_a)).status_code == 404
