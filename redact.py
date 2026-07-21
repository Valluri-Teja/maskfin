"""
redact.py
Full redaction pipeline: PDF or image in, PII detected and blacked out,
redacted file out in the same format, plus an audit log of what was found.
"""

import os
import io
from PIL import Image, ImageDraw
from pdf2image import convert_from_path
import img2pdf

from detectors import detect_pii

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_EXTENSIONS = {".pdf"}


def _redact_image(image: Image.Image) -> tuple:
    detections = detect_pii(image)
    redacted = image.copy()
    draw = ImageDraw.Draw(redacted)
    for d in detections:
        x0, y0, x1, y1 = d["box"]
        draw.rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], fill="black")
    return redacted, detections


def redact_file(input_path: str, output_path: str) -> list:
    ext = os.path.splitext(input_path)[1].lower()
    audit_log = []

    if ext in PDF_EXTENSIONS:
        pages = convert_from_path(input_path, dpi=200)
        redacted_pages = []
        for page_num, page_img in enumerate(pages, start=1):
            redacted_img, detections = _redact_image(page_img)
            redacted_pages.append(redacted_img)
            for d in detections:
                audit_log.append({"page": page_num, "label": d["label"], "text": d["text"]})

        image_bytes_list = []
        for img in redacted_pages:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            image_bytes_list.append(buf.getvalue())
        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(image_bytes_list))

    elif ext in IMAGE_EXTENSIONS:
        img = Image.open(input_path)
        redacted_img, detections = _redact_image(img)
        for d in detections:
            audit_log.append({"page": 1, "label": d["label"], "text": d["text"]})
        redacted_img.save(output_path)

    else:
        raise ValueError(f"Unsupported file type: {ext}. Use PDF, JPG, or PNG.")

    return audit_log


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python redact.py <input_file> <output_file>")
        sys.exit(1)
    log = redact_file(sys.argv[1], sys.argv[2])
    print(f"Redacted {len(log)} item(s):")
    for entry in log:
        print(f"  page {entry['page']}: {entry['label']} -> {entry['text']}")
