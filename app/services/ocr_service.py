import io
from concurrent.futures import ThreadPoolExecutor

import pikepdf
from google.cloud import documentai

from app.config import GCP_PROJECT_ID, DOCUMENT_AI_PROCESSOR_ID
from app.services.llm_service import extract_fields_with_llm
from app.utils.exceptions import ExtractionError

_PAGE_LIMIT = 15


def _split_pdf(pdf_bytes: bytes) -> list[bytes]:
    """Split a PDF into chunks of max _PAGE_LIMIT pages for Document AI processing."""
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
    """Extract fields from PDF using Document AI for OCR and Gemini for field extraction.

    Pipeline:
    1. Split PDF into chunks if needed (Document AI has page limits)
    2. Send chunks to Document AI for OCR
    3. Send OCR text to Gemini LLM for intelligent field extraction

    Returns:
        dict with keys: patient, owner, veterinarian, diagnosis, recommendations
    """
    try:
        # Step 1: Initialize Document AI client
        client = documentai.DocumentProcessorServiceClient()
        processor_name = (
            f"projects/{GCP_PROJECT_ID}/locations/us/processors/{DOCUMENT_AI_PROCESSOR_ID}"
        )

        # Step 2: Process each chunk with Document AI
        def _process_chunk(index: int, chunk: bytes) -> tuple[int, str]:
            document = documentai.RawDocument(content=chunk, mime_type="application/pdf")
            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=document,
                imageless_mode=True
            )
            result = client.process_document(request=request)
            return index, result.document.text

        chunks = _split_pdf(pdf_bytes)
        with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
            futures = [pool.submit(_process_chunk, i, chunk) for i, chunk in enumerate(chunks)]
            parts = sorted((f.result() for f in futures), key=lambda x: x[0])

        full_text = "\n".join(text for _, text in parts)

        # Step 3: Send OCR text to Gemini for intelligent extraction
        return extract_fields_with_llm(full_text)

    except ExtractionError:
        raise
    except Exception as e:
        raise ExtractionError(f"Document AI processing failed: {e}")
