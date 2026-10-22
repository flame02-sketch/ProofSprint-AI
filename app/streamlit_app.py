
from io import BytesIO

import pymupdf
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="ProofSprint AI",
    page_icon="📝",
    layout="centered",
)

st.title("ProofSprint AI")
st.subheader("AI-powered answer evaluation")
st.write(
    "Upload a student's answer sheet to prepare it "
    "for evaluation."
)

uploaded_file = st.file_uploader(
    "Upload an answer sheet",
    type=["pdf", "png", "jpg", "jpeg"],
)

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    file_name = uploaded_file.name.lower()

    st.success(f"Uploaded: {uploaded_file.name}")

    if file_name.endswith(".pdf"):
        try:
            with pymupdf.open(
                stream=file_bytes,
                filetype="pdf",
            ) as document:
                st.write(f"Pages: {len(document)}")

                extracted_text = "\n\n".join(
                    page.get_text()
                    for page in document
                ).strip()

            if extracted_text:
                st.subheader("Extracted text")
                st.text_area(
                    "PDF text preview",
                    value=extracted_text,
                    height=300,
                )
                st.success(
                    "Text extraction completed."
                )
            else:
                st.warning(
                    "No selectable text was found. "
                    "This PDF may contain scanned pages. "
                    "OCR will be added in a later step."
                )

        except (ValueError, RuntimeError, OSError) as error:
            st.error(
                "Could not read this PDF. "
                "Check that the file is valid and "
                "not password-protected."
            )
            st.caption(f"Technical details: {error}")

    else:
        try:
            image = Image.open(BytesIO(file_bytes))
            st.image(
                image,
                caption="Uploaded answer sheet",
                width="stretch",
            )
            st.info(
                "Image uploaded successfully. "
                "Reading text from images will be "
                "added with OCR in a later step."
            )

        except (OSError, ValueError):
            st.error(
                "Could not open this image. "
                "Please upload a valid PNG or JPEG file."
            )
