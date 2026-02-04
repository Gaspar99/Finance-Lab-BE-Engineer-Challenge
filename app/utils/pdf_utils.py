import io

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

            raw = obj.read_raw_bytes()
            # Convert to JPEG via Pillow to normalise format
            pil_image = Image.open(io.BytesIO(raw)).convert("RGB")
            buf = io.BytesIO()
            pil_image.save(buf, format="JPEG")

            filename = f"report_image_{page_number + 1}_{index + 1}.jpeg"
            images.append((filename, buf.getvalue()))

    pdf.close()
    return images
