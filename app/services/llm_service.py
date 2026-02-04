import json

import vertexai
from vertexai.generative_models import GenerativeModel, Image, Part

from app.config import GCP_PROJECT_ID, VERTEX_AI_LOCATION
from app.utils.exceptions import ExtractionError

vertexai.init(project=GCP_PROJECT_ID, location=VERTEX_AI_LOCATION)

_MODEL_NAME = "gemini-2.5-flash"
_CLASSIFICATION_MODEL_NAME = "gemini-2.0-flash-lite"

_EXTRACTION_PROMPT = """You are an expert veterinary report analyzer. Your task is to analyze and understand the content of a veterinary ultrasound/medical report, then extract specific information.

IMPORTANT: This is NOT a simple text extraction task. You must:
1. First, analyze the document structure and understand its format
2. Identify the language(s) used (could be Spanish, English, Portuguese, or mixed)
3. Understand the semantic meaning of sections, not just match keywords
4. Use your reasoning to identify fields even if they use unexpected labels

Return ONLY a valid JSON object with these exact keys:
- patient: The name of the animal/pet being examined
- owner: The name of the person who owns the animal
- veterinarian: The name of the veterinary professional associated with this study (see rules below)
- diagnosis: The complete medical diagnosis, conclusions, or findings as a single clean text
- recommendations: Any treatment recommendations, indications, or follow-up suggestions as a single clean text

Guidelines for analysis:
- The document may be in ANY language (Spanish, English, Portuguese, etc.)
- Field labels vary widely between clinics and countries - do NOT rely on specific keywords

For PATIENT:
- Could be labeled as name, pet name, animal, or just appear near species/breed info

For OWNER:
- Could be labeled as owner, client, responsible party, guardian, or similar concepts

For VETERINARIAN:
- Return ONLY ONE name - the veterinarian who is mentioned in the SAME CONTEXT as the patient information (header section)
- This is usually the referring veterinarian or the professional who requested the study
- Do NOT include the doctors who only appear as signatories at the bottom of the report
- If multiple vets appear in the header, select the one most directly associated with the patient

For DIAGNOSIS and RECOMMENDATIONS:
- Extract the COMPLETE content including all bullet points and items
- FORMAT: Convert to clean, readable text - replace bullet points with dashes or semicolons
- Remove line breaks within the text - return as a single continuous paragraph or semicolon-separated list
- Example: "Hepatic steatosis; Biliary mucocele; Chronic bilateral nephropathy"

General rules:
- Return null for any field that cannot be reliably identified
- Do NOT invent or hallucinate information - only extract what is actually in the text
- Return ONLY the JSON object, no markdown formatting, no code blocks, no explanations

OCR Text:
\"\"\"
{ocr_text}
\"\"\"
"""


def extract_fields_with_llm(ocr_text: str) -> dict:
    """Use Gemini 2.5 Flash to extract structured fields from OCR text.

    Args:
        ocr_text: The raw text extracted from the PDF via Document AI

    Returns:
        dict with keys: patient, owner, veterinarian, diagnosis, recommendations

    Raises:
        ExtractionError: If LLM call fails or response cannot be parsed
    """
    try:
        model = GenerativeModel(_MODEL_NAME)

        prompt = _EXTRACTION_PROMPT.format(ocr_text=ocr_text)

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "max_output_tokens": 4096,
                "response_mime_type": "application/json",
            }
        )

        # Extract the response text
        response_text = response.text.strip()

        # Clean up response if it contains markdown code blocks
        if response_text.startswith("```"):
            # Remove ```json and ``` markers
            lines = response_text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            response_text = "\n".join(lines)

        # Parse JSON response
        fields = json.loads(response_text)

        # Ensure all expected keys exist
        return {
            "patient": fields.get("patient"),
            "owner": fields.get("owner"),
            "veterinarian": fields.get("veterinarian"),
            "diagnosis": fields.get("diagnosis"),
            "recommendations": fields.get("recommendations"),
        }

    except json.JSONDecodeError as e:
        raise ExtractionError(f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        raise ExtractionError(f"LLM extraction failed: {e}")


_CLASSIFICATION_PROMPT = """Analyze this image and determine if it is a REAL medical diagnostic image from a patient examination.

MEDICAL (real diagnostic images from actual examinations):
- Ultrasound scans showing internal organs/tissues (grayscale with anatomical structures)
- X-rays showing bones or internal structures
- MRI/CT scans showing body cross-sections
- Echocardiograms showing heart chambers
- Any clinical imaging with technical overlays (depth markers, frequency, patient data)

NON-MEDICAL (reject these):
- Logos or icons (even if they contain medical symbols like hearts, ECG lines, stethoscopes)
- Signatures or handwriting
- Stamps, watermarks, or letterheads
- Decorative graphics or illustrations
- Simple line drawings or vector graphics
- Company branding or marketing images
- Clipart or stock icons

Key distinction: Real medical images show ACTUAL patient anatomy with complex grayscale detail.
Logos/icons are simplified graphics, often with solid colors or simple shapes.

Respond with ONLY one word: "medical" or "non-medical"
"""


def classify_image(image_bytes: bytes) -> bool:
    """Classify if an image is a medical diagnostic image using Gemini Vision.

    Args:
        image_bytes: Raw image bytes (JPEG format expected)

    Returns:
        True for medical images (ultrasound, X-ray, MRI, etc.)
        False for non-medical (signatures, logos, stamps, etc.)
    """
    model = GenerativeModel(_CLASSIFICATION_MODEL_NAME)
    image = Image.from_bytes(image_bytes)

    response = model.generate_content(
        [_CLASSIFICATION_PROMPT, Part.from_image(image)],
        generation_config={"temperature": 0.1, "max_output_tokens": 32}
    )

    response_text = response.text.strip().lower()
    is_medical = not response_text.startswith("non") and "medical" in response_text

    return is_medical
