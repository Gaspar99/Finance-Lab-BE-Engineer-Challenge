from google.cloud import documentai

from app.config import GCP_PROJECT_ID, DOCUMENT_AI_PROCESSOR_ID
from app.utils.exceptions import ExtractionError

FIELD_MAP = {
    "patient": ["patient", "paciente", "nombre del paciente", "nombre paciente"],
    "owner": ["owner", "propietario", "dueño", "nombre del propietario"],
    "veterinarian": ["veterinarian", "veterinario", "mv", "profesional"],
    "diagnosis": ["diagnosis", "diagnóstico", "diagnóstico presuntivo"],
    "recommendations": ["recommendations", "recomendaciones", "indicaciones"],
}


def extract_fields(pdf_bytes: bytes) -> dict:
    """Send PDF to Document AI and extract the required fields."""
    try:
        client = documentai.DocumentProcessorServiceClient()
        name = client.common_project_path(GCP_PROJECT_ID) + f"/locations/us/processors/{DOCUMENT_AI_PROCESSOR_ID}"

        document = documentai.RawDocument(content=pdf_bytes, mime_type="application/pdf")
        request = documentai.ProcessRequest(name=name, raw_document=document)
        result = client.process_document(request=request)

        return _parse_fields(result.document)
    except ExtractionError:
        raise
    except Exception as e:
        raise ExtractionError(f"Document AI processing failed: {e}")


def _parse_fields(document: documentai.Document) -> dict:
    """Match Document AI entities to our report fields."""
    extracted = {
        "patient": None,
        "owner": None,
        "veterinarian": None,
        "diagnosis": None,
        "recommendations": None,
    }

    for entity in document.entities:
        entity_type = entity.type_.lower().strip()
        for field_name, keywords in FIELD_MAP.items():
            if entity_type in keywords:
                extracted[field_name] = entity.mention_text.strip()
                break

    return extracted
