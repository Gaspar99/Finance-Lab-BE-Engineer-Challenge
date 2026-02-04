import json

import vertexai
from vertexai.generative_models import GenerativeModel

from app.config import GCP_PROJECT_ID, VERTEX_AI_LOCATION
from app.utils.exceptions import ExtractionError

vertexai.init(project=GCP_PROJECT_ID, location=VERTEX_AI_LOCATION)

_MODEL_NAME = "gemini-2.5-flash"

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
                "max_output_tokens": 2048,
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
