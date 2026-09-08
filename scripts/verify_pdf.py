"""Structural checks supplement, but do not replace, rendered-page review."""

from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "output/pdf/ieum-v1-portfolio.pdf"
EXPECTED = ["이음 | 백엔드 개발", "404로 숨기면 안 되는 장애", "테스트가 가드를 실행했는가", "AI 협업 기반의 개발과 검증", "직접 실행하고 판단할 수 있게"]


def verify(path=PDF):
    reader = PdfReader(path)
    if reader.is_encrypted or len(reader.pages) != 5:
        raise ValueError("Expected an unencrypted 5-page PDF")
    if reader.metadata.author != "MaoEmong":
        raise ValueError("Unexpected PDF author")
    faces = set()
    for i, (page, required) in enumerate(zip(reader.pages, EXPECTED), start=1):
        text = page.extract_text()
        if required not in text or "\ufffd" in text or len(text) < 250:
            raise ValueError(f"Text extraction check failed on page {i}")
        if not (594 < float(page.mediabox.width) < 596 and 841 < float(page.mediabox.height) < 843):
            raise ValueError(f"Page {i} is not A4 portrait")
        for ref in page["/Resources"].get("/Font", {}).values():
            font = ref.get_object()
            faces.add(str(font.get('/BaseFont')))
            if font.get("/Subtype") == "/TrueType":
                descriptor = font["/FontDescriptor"]
                if "/FontFile2" not in descriptor or "/ToUnicode" not in font:
                    raise ValueError("Korean font must be embedded and text-extractable")
    if not all(any(face.endswith(name) for face in faces) for name in ('IeumPortfolioSans-Regular', 'IeumPortfolioSans-SemiBold')):
        raise ValueError('Regular and semibold faces must be distinct')
    if not 10_000 < Path(path).stat().st_size < 5_000_000:
        raise ValueError("Unexpected PDF size for a resume attachment")
    print("PASS: 5 A4 pages, Korean text extraction, metadata, embedded fonts, attachment size")


if __name__ == "__main__":
    verify()
