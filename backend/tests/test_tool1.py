"""
test_tool1.py — Tests for tool1_file_reader.

Tests:
  1. Happy path — valid PDF with text layer
  2. Happy path — image file (mocked pytesseract)
  3. Edge case  — PDF with no text layer (OCR fallback)
  4. Failure    — unsupported file extension
  5. Failure    — file not found
  6. Failure    — empty extraction result
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ─── Helpers ───────────────────────────────────────────────────────────────────

SAMPLE_TEXT = "MEDICAL CLAIM\nPolicy ID: POL-2024-GOLD-001\nPatient: Rahul Sharma"


def _make_temp_pdf(tmp_path: Path, text: str | None = SAMPLE_TEXT) -> Path:
    """Create a minimal PDF-like file for testing (content doesn't matter when mocked)."""
    p = tmp_path / "claim.pdf"
    p.write_bytes(b"%PDF-1.4 dummy content for testing")
    return p


def _make_temp_image(tmp_path: Path, ext: str = ".png") -> Path:
    """Create a minimal image file for testing (content doesn't matter when mocked)."""
    from PIL import Image
    p = tmp_path / f"claim{ext}"
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    img.save(str(p))
    return p


# ─── Tests ───────────────────────────────────────────────────────────────────────

class TestTool1FileReader:
    """Tests for the read_file() function."""

    # ── Happy path: PDF with text layer ─────────────────────────────────────

    def test_pdf_text_layer_success(self, tmp_path: Path) -> None:
        """PDF with a text layer should extract text via pdfplumber without OCR."""
        pdf_path = _make_temp_pdf(tmp_path)

        mock_page = MagicMock()
        mock_page.extract_text.return_value = SAMPLE_TEXT
        mock_pdf_ctx = MagicMock()
        mock_pdf_ctx.__enter__ = MagicMock(return_value=mock_pdf_ctx)
        mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdf_ctx.pages = [mock_page]

        with patch("tools.tool1_file_reader.pdfplumber.open", return_value=mock_pdf_ctx):
            from tools.tool1_file_reader import read_file
            result = read_file(str(pdf_path))

        assert result.file_name == "claim.pdf"
        assert result.file_type == "application/pdf"
        assert SAMPLE_TEXT in result.raw_text
        assert result.char_count > 0
        assert result.status == "ok"

    # ── Happy path: image file ──────────────────────────────────────────────

    def test_image_extraction_success(self, tmp_path: Path) -> None:
        """PNG image should be processed via pytesseract and return extracted text."""
        img_path = _make_temp_image(tmp_path, ".png")

        with patch("tools.tool1_file_reader.pytesseract.image_to_string",
                   return_value=SAMPLE_TEXT):
            from tools.tool1_file_reader import read_file
            result = read_file(str(img_path))

        assert result.file_type == "image/png"
        assert result.raw_text == SAMPLE_TEXT
        assert result.char_count == len(SAMPLE_TEXT)
        assert result.status == "ok"

    # ── Edge case: PDF with no text layer (OCR fallback) ──────────────────

    def test_pdf_ocr_fallback(self, tmp_path: Path) -> None:
        """PDF page with no text layer should fall back to OCR."""
        pdf_path = _make_temp_pdf(tmp_path)

        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""   # No text layer
        mock_pil = MagicMock()
        mock_page.to_image.return_value.original = mock_pil

        mock_pdf_ctx = MagicMock()
        mock_pdf_ctx.__enter__ = MagicMock(return_value=mock_pdf_ctx)
        mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdf_ctx.pages = [mock_page]

        with patch("tools.tool1_file_reader.pdfplumber.open", return_value=mock_pdf_ctx), \
             patch("tools.tool1_file_reader.pytesseract.image_to_string",
                   return_value="OCR extracted text"):
            from tools.tool1_file_reader import read_file
            result = read_file(str(pdf_path))

        assert "OCR extracted text" in result.raw_text
        assert "OCR fallback" in result.status

    # ── Failure: unsupported file type ──────────────────────────────────────

    def test_unsupported_file_type(self, tmp_path: Path) -> None:
        """Files with unsupported extensions should raise ValueError."""
        weird_path = tmp_path / "document.docx"
        weird_path.write_bytes(b"PK fake docx content")

        from tools.tool1_file_reader import read_file
        with pytest.raises(ValueError, match="Unsupported file type"):
            read_file(str(weird_path))

    # ── Failure: file not found ──────────────────────────────────────────────

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Non-existent file path should raise FileNotFoundError."""
        from tools.tool1_file_reader import read_file
        with pytest.raises(FileNotFoundError):
            read_file(str(tmp_path / "ghost.pdf"))

    # ── Failure: empty extraction ────────────────────────────────────────────

    def test_empty_extraction_raises(self, tmp_path: Path) -> None:
        """Empty extraction result should raise ValueError."""
        pdf_path = _make_temp_pdf(tmp_path)

        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_page.to_image.return_value.original = MagicMock()

        mock_pdf_ctx = MagicMock()
        mock_pdf_ctx.__enter__ = MagicMock(return_value=mock_pdf_ctx)
        mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
        mock_pdf_ctx.pages = [mock_page]

        with patch("tools.tool1_file_reader.pdfplumber.open", return_value=mock_pdf_ctx), \
             patch("tools.tool1_file_reader.pytesseract.image_to_string",
                   return_value=""):   # OCR also returns empty
            from tools.tool1_file_reader import read_file
            with pytest.raises(ValueError, match="No text could be extracted"):
                read_file(str(pdf_path))
