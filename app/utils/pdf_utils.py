import fitz  # PyMuPDF


def extract_images(pdf_bytes: bytes) -> list[tuple[str, bytes]]:
    """Extract all images from a PDF. Returns a list of (filename, image_bytes) tuples."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []

    for page_number in range(len(doc)):
        page = doc.load_page(page_number)
        image_list = page.get_images(full=True)

        for index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            filename = f"report_image_{page_number + 1}_{index + 1}.{image_ext}"
            images.append((filename, image_bytes))

    doc.close()
    return images
