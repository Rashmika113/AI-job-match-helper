import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from jobmatch.loader import clean_text, read_upload


def test_reads_pdf(tmp_path):
    path = tmp_path / "cv.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawString(72, 720, "Skills: Python, SQL, Docker")
    c.save()
    text = read_upload("cv.pdf", path.read_bytes())
    assert "Python, SQL, Docker" in text


def test_reads_txt_with_sinhala():
    assert read_upload("cv.txt", "නම: නිමල්\nPython".encode()) == "නම: නිමල්\nPython"


def test_rejects_other_types():
    with pytest.raises(ValueError):
        read_upload("cv.docx", b"...")


def test_clean_text_keeps_paragraphs():
    assert clean_text("a   b\r\n\r\n\r\nc\t d") == "a b\n\nc d"
