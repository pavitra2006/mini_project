# app.py
# Optional: Streamlit UI for OCR Document Sorter

import streamlit as st

def main():
    st.title("OCR Document Sorter")
    st.write("Select a folder to categorize files by extension.")

    import os
    import shutil

    uploaded_files = st.file_uploader(
        "Upload multiple files to categorize by extension:",
        type=["jpg", "jpeg", "png", "pdf", "docx", "xlsx", "exe", "zip", "msi", "pcap", "webp", "unknown"],
        accept_multiple_files=True
    )
    if st.button("Categorize and Download as ZIP"):
        if not uploaded_files:
            st.error("No files uploaded.")
            return

        import io
        import zipfile
        from PyPDF2 import PdfReader

        def classify_pdf(file_bytes):
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                text = text.lower()
                if any(word in text for word in ["certificate", "completion", "certify"]):
                    return "certificate"
                elif any(word in text for word in ["id card", "identity", "passport", "aadhaar", "pan card"]):
                    return "id_card"
                elif any(word in text for word in ["invoice", "bill", "amount due", "total due"]):
                    return "invoice"
                else:
                    return "pdf_other"
            except Exception:
                return "pdf_error"

        categorized_files = {"certificate": [], "id_card": [], "invoice": [], "pdf_other": [], "pdf_error": []}
        other_ext_map = {}
        for uploaded_file in uploaded_files:
            fname = uploaded_file.name
            ext = os.path.splitext(fname)[1].lower().strip('.')
            file_bytes = uploaded_file.read()
            if ext == "pdf":
                category = classify_pdf(file_bytes)
                categorized_files[category].append((fname, file_bytes))
            else:
                other_ext_map.setdefault(ext, []).append((fname, file_bytes))

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            # Add categorized PDFs
            for category, files in categorized_files.items():
                for fname, file_bytes in files:
                    zipf.writestr(os.path.join(category, fname), file_bytes)
            # Add other files by extension
            for ext, files in other_ext_map.items():
                for fname, file_bytes in files:
                    zipf.writestr(os.path.join(ext, fname), file_bytes)
        zip_buffer.seek(0)
        st.success("Files categorized and ready for download as a zip file.")
        st.download_button(
            label="Download All Categorized Files (ZIP)",
            data=zip_buffer,
            file_name="categorized_files.zip",
            mime="application/zip"
        )

if __name__ == "__main__":
    main()
