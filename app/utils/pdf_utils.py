import io
from concurrent.futures import ThreadPoolExecutor

import pikepdf
from PIL import Image


def extract_images(pdf_bytes: bytes) -> list[tuple[str, bytes]]:
    """Extract all images from a PDF. Returns a list of (filename, image_bytes) tuples."""
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    images = []

    for page_number, page in enumerate(pdf.pages):
        for index, (name, obj) in enumerate(page.resources.get("/XObject", {}).items()):
            if obj.get("/Subtype") != pikepdf.Name("/Image"):
                continue

            try:
                try:
                    data = obj.read_bytes()
                except Exception:
                    data = obj.read_raw_bytes()

                pil_image = Image.open(io.BytesIO(data)).convert("RGB")
                buf = io.BytesIO()
                pil_image.save(buf, format="JPEG")
            except Exception:
                continue

            filename = f"report_image_{page_number + 1}_{index + 1}.jpeg"
            images.append((filename, buf.getvalue()))

    pdf.close()
    return images


def filter_medical_images(images: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    """Filter images to keep only medical diagnostic images using parallel classification.

    Uses Gemini Vision to classify each image as medical or non-medical.
    Images are classified in parallel for better performance.

    Args:
        images: List of (filename, image_bytes) tuples

    Returns:
        Filtered list containing only medical diagnostic images
    """
    if not images:
        return []

    from app.services.llm_service import classify_image

    def _classify(item: tuple[str, bytes]) -> tuple[str, bytes, bool]:
        filename, data = item
        try:
            is_medical = classify_image(data)
        except Exception:
            # Fail-open: keep image if classification fails
            is_medical = True
        return (filename, data, is_medical)

    with ThreadPoolExecutor(max_workers=min(len(images), 5)) as pool:
        results = list(pool.map(_classify, images))

    return [(fn, data) for fn, data, is_medical in results if is_medical]
