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
