# DiagnoVET - Veterinary Report Processing API

REST API for processing veterinary ultrasound/radiology PDF reports. Extracts patient information, diagnosis, and images using Google Cloud services.

## Live API

**Base URL:** `https://diagnovet-api-744871887039.southamerica-east1.run.app`

**API Key:** Contact me for the test API key.

## API Endpoints

### POST /reports

Upload a PDF report for processing.

**Headers:**
- `X-API-Key`: API key (required)

**Body:** `multipart/form-data` with `file` field containing the PDF

**Response (201):**
```json
{
  "id": "uuid",
  "created_at": "2026-02-04T18:00:00Z",
  "status": "completed",
  "original_filename": "report.pdf",
  "patient": "Lola",
  "owner": "María García",
  "veterinarian": "Dr. Juan Pérez",
  "diagnosis": "Hepatic steatosis; Biliary mucocele",
  "recommendations": "Follow-up in 30 days",
  "images": [
    {
      "filename": "report_image_1_1.jpeg",
      "url": "https://storage.googleapis.com/..."
    }
  ]
}
```

### GET /reports/{report_id}

Retrieve a previously processed report.

**Headers:**
- `X-API-Key`: API key required

**Response (200):** Same structure as POST response. Image URLs are regenerated on each request since signed URLs expire after 15 minutes.

## GCP Services

- **Cloud Run**: Serverless container hosting with automatic scaling
- **Document AI**: OCR processor for text extraction from PDFs
- **Vertex AI**: Gemini 2.5 Flash for intelligent field extraction
- **Cloud Storage**: Private bucket for image storage with signed URL access
- **Firestore**: NoSQL database for report persistence
- **Secret Manager**: Secure API key storage

## Project Structure

```
app/
├── main.py                 # FastAPI entry point
├── config.py               # Environment configuration
├── api/
│   ├── routes.py           # POST /reports, GET /reports/{id}
│   └── dependencies.py     # API key validation middleware
├── services/
│   ├── pdf_processor.py    # Orchestrates the processing pipeline
│   ├── ocr_service.py      # Document AI integration + PDF chunking
│   ├── llm_service.py      # Gemini prompt and response handling
│   ├── storage_service.py  # GCS upload and signed URL generation
│   └── firestore_service.py # Report CRUD operations
└── utils/
    ├── pdf_utils.py        # Image extraction from PDFs using pikepdf
    └── exceptions.py       # Custom exception classes
```

## Technical Decisions

### Why Vertex AI Gemini for field extraction?

Veterinary reports come in many formats and layouts. Gemini 2.5 Flash can semantically understand the document structure and extract fields regardless of specific labels or formatting. The model is configured with `response_mime_type: application/json` to guarantee valid JSON output.

### Why Document AI + Gemini (two-step pipeline)?

Document AI excels at OCR - converting PDF pages to text with high accuracy. Gemini excels at understanding and extracting structured data from unstructured text. Combining them leverages the strengths of each: reliable text extraction followed by intelligent field identification.

### Why signed URLs instead of public images?

Signed URLs provide time-limited access (15 minutes) without requiring additional authentication. URLs are regenerated on each GET request, ensuring fresh access tokens.

### Why regenerate URLs on GET instead of storing them?

Signed URLs expire. Storing them in the database would mean returning expired links. Regenerating on each request ensures the client always receives working URLs.

### Why Secret Manager for API keys?

Hardcoding secrets or using environment variables for sensitive data is insecure. The Cloud Run service account accesses the secret at runtime.

## Security Considerations

- API key authentication on all endpoints
- API key stored in Secret Manager, not in code or environment variables
- Images served via time-limited signed URLs (15 min expiry)
- Cloud Run service account follows least-privilege principle
- No sensitive data logged or exposed in error messages
