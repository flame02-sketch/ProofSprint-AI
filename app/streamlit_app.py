from io import BytesIO

import pymupdf
import pytesseract
import streamlit as st
from PIL import Image

# Tell Python where Tesseract is installed on Windows.
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_pdf_text(file_bytes: bytes) -> tuple[str, int]:
    """Extract selectable text or use OCR for scanned PDF pages."""
    extracted_pages = []

    with pymupdf.open(stream=file_bytes, filetype="pdf") as document:
        page_count = len(document)

        for page_number, page in enumerate(document, start=1):
            text = page.get_text().strip()

            if not text:
                pixmap = page.get_pixmap(dpi=200, alpha=False)
                image_bytes = pixmap.tobytes("png")

                with Image.open(BytesIO(image_bytes)) as image:
                    text = pytesseract.image_to_string(
                        image,
                        lang="eng",
                    ).strip()

            if text:
                extracted_pages.append(f"--- Page {page_number} ---\n{text}")
            else:
                extracted_pages.append(
                    f"--- Page {page_number} ---\n[No text recognized]"
                )

    return "\n\n".join(extracted_pages), page_count


def extract_image_text(image_bytes: bytes) -> tuple[Image.Image, str]:
    """Open an image and recognize its English text using OCR."""
    with Image.open(BytesIO(image_bytes)) as source:
        image = source.convert("RGB")

    text = pytesseract.image_to_string(image, lang="eng").strip()
    return image, text


def main() -> None:
    st.set_page_config(
        page_title="ProofSprint AI",
        page_icon="📝",
        layout="centered",
    )

    st.title("ProofSprint AI")
    st.subheader("AI-powered answer evaluation")
    st.write("Upload a student's answer sheet to prepare it for evaluation.")

    uploaded_file = st.file_uploader(
        "Upload an answer sheet",
        type=["pdf", "png", "jpg", "jpeg"],
    )

    if uploaded_file is None:
        st.info("Upload a PDF or image to get started.")
        return

    file_bytes = uploaded_file.getvalue()
    file_name = uploaded_file.name.lower()

    st.success(f"Uploaded: {uploaded_file.name}")

    try:
        if file_name.endswith(".pdf"):
            with st.spinner("Reading PDF and checking for scanned pages..."):
                extracted_text, page_count = extract_pdf_text(file_bytes)

            st.write(f"Pages: {page_count}")
            st.subheader("Extracted text")

            if extracted_text.strip():
                st.text_area(
                    "PDF text preview",
                    value=extracted_text,
                    height=350,
                )
                st.success("PDF text processing completed.")
            else:
                st.warning("No text could be extracted from this PDF.")

        else:
            with st.spinner("Reading image and recognizing text..."):
                image, extracted_text = extract_image_text(file_bytes)

            st.image(
                image,
                caption="Uploaded answer sheet",
                width="stretch",
            )

            st.subheader("Recognized text")

            if extracted_text:
                st.text_area(
                    "Image text preview",
                    value=extracted_text,
                    height=300,
                )
                st.success("Image OCR completed.")
            else:
                st.warning(
                    "No text was recognized. Try a clearer, "
                    "well-lit image with readable printed text."
                )

    except (
        OSError,
        RuntimeError,
        ValueError,
        pymupdf.FileDataError,
    ) as error:
        st.error("We couldn't process this file. Check that it is valid and try again.")
        st.caption(f"Technical details: {error}")


if __name__ == "__main__":
    main()
