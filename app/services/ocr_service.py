import io
import re

import pikepdf
from google.cloud import documentai

from app.config import GCP_PROJECT_ID, DOCUMENT_AI_PROCESSOR_ID
from app.utils.exceptions import ExtractionError

_PAGE_LIMIT = 15 

_PATIENT_RE = re.compile(r"(?i)(?:paciente|patient)\s*:\s*(.+)")
_OWNER_RE = re.compile(r"(?i)(?:propietario|owner|dueño)\s*:\s*(.+)")
_VET_RE = re.compile(r"(?i)(?:referido\s+por|veterinario|profesional)\s*:\s*(.+)")
_SECTION_BREAK = r"(?=\n[A-Z][A-Z ]{3,}\n|\Z)"
_CONCLUSION_RE = re.compile(r"(?i)CONCLUSION\s*\n(.*?)" + _SECTION_BREAK, re.DOTALL)
_RECOMMENDATIONS_RE = re.compile(r"(?i)(?:recomendaciones|indicaciones)\s*[:\n]\s*(.*?)" + _SECTION_BREAK, re.DOTALL)


def _split_pdf(pdf_bytes: bytes) -> list[bytes]:
    
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    total = len(pdf.pages)
    if total <= _PAGE_LIMIT:
        pdf.close()
        return [pdf_bytes]

    chunks: list[bytes] = []
    for start in range(0, total, _PAGE_LIMIT):
        chunk_pdf = pikepdf.new()
        for page in pdf.pages[start:start + _PAGE_LIMIT]:
            chunk_pdf.pages.append(page)
        buf = io.BytesIO()
        chunk_pdf.save(buf)
        chunks.append(buf.getvalue())
        chunk_pdf.close()

    pdf.close()
    return chunks


def extract_fields(pdf_bytes: bytes) -> dict:
    """Send PDF to Document AI (chunked if >30 pages) and extract fields."""
    try:
        client = documentai.DocumentProcessorServiceClient()
        name = client.common_project_path(GCP_PROJECT_ID) + f"/locations/us/processors/{DOCUMENT_AI_PROCESSOR_ID}"

        # Process each chunk and join all OCR text
        full_text_parts: list[str] = []
        for chunk in _split_pdf(pdf_bytes):
            document = documentai.RawDocument(content=chunk, mime_type="application/pdf")
            request = documentai.ProcessRequest(name=name, raw_document=document, imageless_mode=True)
            result = client.process_document(request=request)
            full_text_parts.append(result.document.text)

        full_text = "\n".join(full_text_parts)

        # DEBUG — dump full OCR text
        print(f"[DOC-AI TEXT]\n{full_text}\n[/DOC-AI TEXT]", flush=True)

        return _parse_fields_from_text(full_text)
    except ExtractionError:
        raise
    except Exception as e:
        raise ExtractionError(f"Document AI processing failed: {e}")


def _first_match(pattern: re.Pattern, text: str) -> str | None:
    """Return the first captured group stripped, or None."""
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def _parse_fields_from_text(text: str) -> dict:
    """Extract fields from the full OCR'd text using label-based regex."""
    return {
        "patient": _first_match(_PATIENT_RE, text),
        "owner": _first_match(_OWNER_RE, text),
        "veterinarian": _first_match(_VET_RE, text),
        "diagnosis": _first_match(_CONCLUSION_RE, text),
        "recommendations": _first_match(_RECOMMENDATIONS_RE, text),
    }
