"""
tool1_file_reader.py — Tool 1: Document ingestion using multimodal LLM OCR.

Accepts a file path (PDF or image) and returns extracted plain text.
Uses pdfplumber for digital PDFs and Gemini 2.0 Flash (via OpenRouter) as a 
high-performance multimodal OCR for scanned documents and images.
"""

from __future__ import annotations

import os
import base64
from pathlib import Path
from io import BytesIO
from typing import Any

import pdfplumber
from PIL import Image
from openai import OpenAI

from models.schemas import FileReadResult
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL

# Initialise multimodal client
_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

# Supported file-type groups
_PDF_EXTS = {".pdf"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif"}

def _encode_image(image: Image.Image) -> str:
    """Helper to convert PIL Image to base64 string."""
    buffered = BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode()

def _ocr_with_gemini(images: list[Image.Image]) -> str:
    """Uses Gemini 2.0 Flash via OpenRouter to perform high-accuracy OCR."""
    if not images:
        return ""
    
    # Prepare multimodal message
    content = [{"type": "text", "text": "Transcribe all text from these document pages accurately. Return ONLY the transcribed text."}]
    for img in images[:5]: # Limit to first 5 pages for speed/limit
        b64 = _encode_image(img)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
        })

    try:
        response = _client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": content}],
            max_tokens=4000
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(f"Multimodal OCR failed: {e}")

def _extract_text_from_pdf(path: Path) -> tuple[str, str]:
    """Extract text from PDF with multimodal fallback."""
    texts = []
    images_for_ocr = []
    
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and len(text.strip()) > 50: # Threshold for digital text
                texts.append(text.strip())
            else:
                # Scanned or low-text page -> render for multimodal OCR
                images_for_ocr.append(page.to_image(resolution=150).original)
    
    if images_for_ocr:
        ocr_text = _ocr_with_gemini(images_for_ocr)
        texts.append(ocr_text)
        status = "ok (multimodal OCR applied)"
    else:
        status = "ok (native text)"
        
    return "\n\n".join(texts).strip(), status

def _extract_text_from_image(path: Path) -> tuple[str, str]:
    """Extract text from image using multimodal LLM."""
    img = Image.open(str(path)).convert("RGB")
    text = _ocr_with_gemini([img])
    return text, "ok (multimodal OCR)"

def read_file(file_path: str) -> FileReadResult:
    """Main entry point for Tool 1."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    file_name = path.name

    if ext in _PDF_EXTS:
        file_type = "application/pdf"
        raw_text, status = _extract_text_from_pdf(path)
    elif ext in _IMAGE_EXTS:
        file_type = f"image/{ext.lstrip('.')}"
        raw_text, status = _extract_text_from_image(path)
    else:
        raise ValueError(f"Unsupported extension: {ext}")

    if not raw_text or not raw_text.strip():
        raise ValueError("Extraction yielded no text content.")

    return FileReadResult(
        file_name=file_name,
        char_count=len(raw_text),
        file_type=file_type,
        raw_text=raw_text,
        status=status
    )
