# OCR Document Sorter

## Overview
This project is a Streamlit-based web application that allows users to upload multiple files (including PDFs, images, and other document types), automatically categorizes them by file extension, and further classifies PDF files into categories such as certificate, id_card, and invoice using simple keyword-based text extraction. All categorized files are provided to the user as a downloadable ZIP archive.

## Features
- Upload multiple files at once (supports: jpg, jpeg, png, pdf, docx, xlsx, exe, zip, msi, pcap, webp, unknown)
- PDF files are scanned and classified into:
  - certificate
  - id_card
  - invoice
  - pdf_other (if not matched)
  - pdf_error (if unreadable)
- All other files are grouped by their extension
- Download all categorized files as a single ZIP file
- Works in all modern browsers and adapts to browser theme (light/dark)

## How to Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the Streamlit app:
   ```bash
   streamlit run ocr_document_sorter/app.py
   ```
3. Open the provided local URL in your browser (e.g., Google Chrome)
4. Upload your files, click "Categorize and Download as ZIP", and download the categorized archive

## File Structure
- `ocr_document_sorter/app.py` - Main Streamlit UI and logic
- `ocr_document_sorter/requirements.txt` - Python dependencies
- `ocr_document_sorter/ocr_utils.py` - (Placeholder for OCR utilities)
- `ocr_document_sorter/train_classifier.py` - (Placeholder for training logic)
- `ocr_document_sorter/predict.py` - (Placeholder for prediction logic)
- `ocr_document_sorter/data/` - Example data folders (not used by the app directly)

## Customization
- To improve PDF classification, enhance the `classify_pdf` function in `app.py` with more advanced logic or ML models.
- To support more file types, add them to the `type` list in the file uploader widget.

## Requirements
- Python 3.8+
- See `requirements.txt` for all required packages

## Security Note
- The app does not save files to disk or server; all processing is in-memory and files are only available to the user as a ZIP download.

## License
MIT License (or specify your own)