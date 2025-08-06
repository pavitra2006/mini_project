# app.py
# Optional: Streamlit UI for OCR Document Sorter

import streamlit as st
import os
from dotenv import load_dotenv

def main():
    st.title("OCR Document Sorter")
    st.write("Select a folder to categorize files by extension.")

    # Load environment variables from .env file
    load_dotenv()

    # NOTE: The upload limit is set in .streamlit/config.toml (maxUploadSize = 200)
    # If you see a 413 error, reduce file size or increase the limit in config.toml and restart Streamlit.
    uploaded_files = st.file_uploader(
        "Upload multiple files to categorize by extension:",
        type=["jpg", "jpeg", "png", "pdf", "docx", "xlsx", "exe", "ex_", "bin", "zip", "msi", "pcap", "webp", "unknown"],
        accept_multiple_files=True
    )
    st.write("Uploaded files:", uploaded_files)
    st.info("Google Cloud Vision API will be used for OCR on images and PDFs. Set up your Google credentials as described in the README.")
    if st.button("Categorize and Download as ZIP"):
        if not uploaded_files:
            st.error("No files uploaded.")
            return

        import io
        import zipfile
        from google.cloud import vision
        from google.cloud import language_v1
        from PyPDF2 import PdfReader


        # Initialize Google Vision and Language clients
        try:
            vision_client = vision.ImageAnnotatorClient()
            lang_client = language_v1.LanguageServiceClient()
        except Exception as e:
            st.error(f"Google Cloud API client error: {e}")
            return

        def extract_text_gcv(file_bytes):
            image = vision.Image(content=file_bytes)
            response = vision_client.document_text_detection(image=image)
            if response.error.message:
                return ""
            return response.full_text_annotation.text

        def analyze_text_nlp(text):
            document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
            # Entity analysis
            entities = lang_client.analyze_entities(request={"document": document}).entities
            entity_list = [(entity.name, language_v1.Entity.Type(entity.type_).name) for entity in entities]
            # Sentiment analysis
            sentiment = lang_client.analyze_sentiment(request={"document": document}).document_sentiment
            return entity_list, sentiment.score, sentiment.magnitude

        def classify_text(text):
            text = text.lower()
            if any(word in text for word in ["certificate", "completion", "certify"]):
                return "certificate"
            elif any(word in text for word in ["id card", "identity", "passport", "aadhaar", "pan card"]):
                return "id_card"
            elif any(word in text for word in ["invoice", "bill", "amount due", "total due"]):
                return "invoice"
            else:
                return "other"

        categorized_files = {
            "certificate": [],
            "id_card": [],
            "invoice": [],
            "exe": [],
            "zip": [],
            "other": [],
            "pdf_error": []
        }
        report_files = []
        other_ext_map = {}
        for uploaded_file in uploaded_files:
            fname = uploaded_file.name
            ext = os.path.splitext(fname)[1].lower().strip('.')
            file_bytes = uploaded_file.read()
            text = ""
            if ext == "pdf":
                # Extract text from each page using PyPDF2
                try:
                    reader = PdfReader(io.BytesIO(file_bytes))
                    for page in reader.pages:
                        page_text = page.extract_text() or ""
                        text += page_text
                    category = classify_text(text)
                    categorized_files[category].append((fname, file_bytes))
                except Exception:
                    categorized_files["pdf_error"].append((fname, file_bytes))
            elif ext in ["jpg", "jpeg", "png", "webp"]:
                # Use Google Vision for image OCR
                try:
                    text = extract_text_gcv(file_bytes)
                    category = classify_text(text)
                    categorized_files[category].append((fname, file_bytes))
                except Exception:
                    categorized_files["other"].append((fname, file_bytes))
            elif ext in ["exe", "ex_", "bin"]:
                categorized_files["exe"].append((fname, file_bytes))
            elif ext == "zip":
                categorized_files["zip"].append((fname, file_bytes))
            else:
                other_ext_map.setdefault(ext, []).append((fname, file_bytes))

            # If text was extracted, analyze with Google NLP and save a report
            if text.strip():
                try:
                    entities, sentiment_score, sentiment_magnitude = analyze_text_nlp(text)
                    report = f"File: {fname}\nCategory: {category}\nSentiment Score: {sentiment_score}\nSentiment Magnitude: {sentiment_magnitude}\nEntities: {entities}\n"
                    report_files.append((fname + "_report.txt", report.encode("utf-8")))
                except Exception as e:
                    report = f"File: {fname}\nCategory: {category}\nNLP Analysis Error: {e}\n"
                    report_files.append((fname + "_report.txt", report.encode("utf-8")))

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            # Add categorized files
            for category, files in categorized_files.items():
                for fname, file_bytes in files:
                    zipf.writestr(os.path.join(category, fname), file_bytes)
            # Add other files by extension
            for ext, files in other_ext_map.items():
                for fname, file_bytes in files:
                    zipf.writestr(os.path.join(ext, fname), file_bytes)
            # Add NLP reports
            for report_fname, report_bytes in report_files:
                zipf.writestr(os.path.join("reports", report_fname), report_bytes)
        zip_buffer.seek(0)
        st.success("Files categorized (using Google AI/ML for OCR & NLP) and ready for download as a zip file.")
        st.download_button(
            label="Download All Categorized Files (ZIP)",
            data=zip_buffer,
            file_name="categorized_files.zip",
            mime="application/zip"
        )

if __name__ == "__main__":
    main()
