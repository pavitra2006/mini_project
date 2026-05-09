# app.py
# Optional: Streamlit UI for OCR Document Sorter

import streamlit as st
import os
from dotenv import load_dotenv

def main():
    # Print Streamlit version and environment for debugging
    st.write(f"Streamlit version: {st.__version__}")
    st.write(f"Running in: {os.environ.get('STREAMLIT_SERVER_HEADLESS', 'unknown')}")
    # If file uploads still do not work, ensure you are running with 'streamlit run app.py' and not 'python app.py'.
    st.title("OCR Document Sorter")
    st.write("Select a folder to categorize files by extension.")

    # Load environment variables from .env file
    load_dotenv()

    # NOTE: The upload limit is set in .streamlit/config.toml (maxUploadSize = 200)
    # If you see a 413 error, reduce file size or increase the limit in config.toml and restart Streamlit.
    uploaded_files = st.file_uploader(
        "Upload one or more files to categorize:",
        accept_multiple_files=True
    )
    st.write("Uploaded files (raw):", uploaded_files)
    st.info("If file uploads are not working: 1) Make sure you are running Streamlit in a browser, not in a terminal or notebook. 2) If using a remote dev container or Codespace, check that file uploads are supported in your environment. 3) Try a different browser or clear your cache. 4) Restart the Streamlit app after any config changes.")
    if uploaded_files:
        st.write(f"Number of files uploaded: {len(uploaded_files)}")
        for f in uploaded_files:
            st.write(f"File: {f.name}, Size: {getattr(f, 'size', 'unknown')}, Type: {getattr(f, 'type', 'unknown')}")
    else:
        st.info("Upload files above before clicking the categorize button.")
    st.info("Google Cloud Vision API will be used for OCR on images and PDFs if credentials are configured. Otherwise the app will still categorize files by extension and extract PDF text locally.")
    if st.button("Categorize and Download as ZIP"):
        if not uploaded_files:
            st.error("No files uploaded.")
            return

        import io
        import zipfile
        from PyPDF2 import PdfReader
        use_gcp = False
        vision_client = None
        lang_client = None

        def extract_text_local(file_bytes):
            try:
                from PIL import Image
                import pytesseract
                image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
                return pytesseract.image_to_string(image)
            except Exception:
                return ""

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

        def extract_text_gcv(file_bytes):
            try:
                image = vision.Image(content=file_bytes)
                response = vision_client.document_text_detection(image=image)
                if response.error.message:
                    return ""
                return response.full_text_annotation.text
            except Exception as e:
                # Silently fall back to local OCR on API errors
                return extract_text_local(file_bytes)

        def analyze_text_nlp(text):
            try:
                document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
                entities = lang_client.analyze_entities(request={"document": document}).entities
                entity_list = [(entity.name, language_v1.Entity.Type(entity.type_).name) for entity in entities]
                sentiment = lang_client.analyze_sentiment(request={"document": document}).document_sentiment
                return entity_list, sentiment.score, sentiment.magnitude
            except Exception as e:
                # Silently skip NLP analysis on API errors
                return [], 0.0, 0.0

        def load_gcp_credentials():
            try:
                from google.oauth2 import service_account
                
                def safe_secret(key):
                    try:
                        return st.secrets.get(key)
                    except Exception:
                        return None
                
                # Fallback to environment variable first
                api_key = os.getenv("GOOGLE_API_KEY")
                if api_key:
                    return {"api_key": api_key}
                
                # Try service account credentials from file path
                key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                if key_path and os.path.isfile(key_path):
                    return service_account.Credentials.from_service_account_file(key_path)
                
                # Try API key from Streamlit secrets
                api_key = safe_secret("gcp")
                if isinstance(api_key, dict):
                    api_key = api_key.get("api_key")
                if api_key:
                    return {"api_key": api_key}
                
                # Try service account from Streamlit secrets
                service_account_info = safe_secret("gcp_service_account")
                if service_account_info:
                    return service_account.Credentials.from_service_account_info(dict(service_account_info))
            except Exception:
                pass
            return None

        try:
            from google.cloud import vision
            from google.cloud import language_v1
            credentials = load_gcp_credentials()
            if credentials:
                if isinstance(credentials, dict) and "api_key" in credentials:
                    vision_client = vision.ImageAnnotatorClient(client_options={"api_key": credentials["api_key"]})
                    lang_client = language_v1.LanguageServiceClient(client_options={"api_key": credentials["api_key"]})
                else:
                    vision_client = vision.ImageAnnotatorClient(credentials=credentials)
                    lang_client = language_v1.LanguageServiceClient(credentials=credentials)
                use_gcp = True
            else:
                st.info("Google Cloud credentials not found. Using local OCR for file processing.")
        except Exception as e:
            st.info("Google Cloud API not fully configured. Using local OCR for file processing.")

        categorized_files = {
            "certificate": [],
            "id_card": [],
            "invoice": [],
            "exe": [],
            "zip": [],
            "images": [],
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
            category = None

            if ext == "pdf":
                try:
                    reader = PdfReader(io.BytesIO(file_bytes))
                    for page in reader.pages:
                        page_text = page.extract_text() or ""
                        text += page_text
                    category = classify_text(text)
                    categorized_files[category].append((fname, file_bytes))
                except Exception:
                    categorized_files["pdf_error"].append((fname, file_bytes))
            elif ext in ["jpg", "jpeg", "png"]:
                if use_gcp:
                    text = extract_text_gcv(file_bytes)
                else:
                    text = extract_text_local(file_bytes)
                category = classify_text(text) if text.strip() else "images"
                categorized_files[category].append((fname, file_bytes))
            elif ext == "webp":
                if use_gcp:
                    text = extract_text_gcv(file_bytes)
                    category = classify_text(text)
                    categorized_files[category].append((fname, file_bytes))
                else:
                    categorized_files["images"].append((fname, file_bytes))
            elif ext in ["exe", "ex_", "bin"]:
                categorized_files["exe"].append((fname, file_bytes))
            elif ext == "zip":
                categorized_files["zip"].append((fname, file_bytes))
            else:
                other_ext_map.setdefault(ext, []).append((fname, file_bytes))

            if text.strip():
                if use_gcp:
                    try:
                        entities, sentiment_score, sentiment_magnitude = analyze_text_nlp(text)
                        report = f"File: {fname}\nCategory: {category or 'unknown'}\nSentiment Score: {sentiment_score}\nSentiment Magnitude: {sentiment_magnitude}\nEntities: {entities}\n"
                    except Exception as e:
                        report = f"File: {fname}\nCategory: {category or 'unknown'}\nNLP Analysis Error: {e}\n"
                else:
                    report = f"File: {fname}\nCategory: {category or 'unknown'}\nExtracted Text:\n{text}\n"
                report_files.append((fname + "_report.txt", report.encode("utf-8")))

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for category_name, files in categorized_files.items():
                for fname, file_bytes in files:
                    zipf.writestr(os.path.join(category_name, fname), file_bytes)
            for ext_name, files in other_ext_map.items():
                for fname, file_bytes in files:
                    zipf.writestr(os.path.join(ext_name, fname), file_bytes)
            for report_fname, report_bytes in report_files:
                zipf.writestr(os.path.join("reports", report_fname), report_bytes)
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
