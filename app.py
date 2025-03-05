import streamlit as st
import pandas as pd
import subprocess
import os
import re
import PyPDF2
import pytesseract
from pdf2image import convert_from_path

# Function to detect JBIG2 compression in a PDF
def detect_jbig2(pdf_path):
    """Runs pdf-parser.py to check for JBIG2 streams."""
    try:
        result = subprocess.run(["python3", "pdf-parser.py", "-search", "JBIG2Decode", pdf_path], capture_output=True, text=True)
        return "JBIG2Decode" in result.stdout
    except Exception as e:
        return f"Error detecting JBIG2: {e}"

# Function to extract text using OCR from JBIG2 images
def extract_text_from_images(pdf_path):
    try:
        images = convert_from_path(pdf_path, fmt="png")
        extracted_text = ""
        for img in images:
            extracted_text += pytesseract.image_to_string(img)
        return extracted_text.strip()
    except Exception as e:
        return f"Error extracting text from images: {e}"

# Function to extract visible text from a PDF
def extract_visible_text(pdf_path):
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text
    except Exception as e:
        return f"Error extracting visible text: {e}"

# Function to find financial markers in text
def extract_financial_data(text):
    patterns = {
        "Bank Account Numbers": re.findall(r'\b\d{8,12}\b', text),
        "Routing Numbers": re.findall(r'\b\d{9}\b', text),
        "Credit Card Numbers": re.findall(r'\b\d{13,16}\b', text),
        "Monetary Values": re.findall(r'\b\d{1,3}(,\d{3})*(\.\d{2})?\b', text)
    }
    return {key: values for key, values in patterns.items() if values}

# Streamlit UI
st.title("Shiva PDF Analyzer (With JBIG2 OCR Extraction)")

uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

if uploaded_file:
    pdf_path = f"/tmp/{uploaded_file.name}"
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.read())

    st.write("🔍 Processing the PDF...")

    # Detect JBIG2 compression
    st.subheader("📂 JBIG2 Compression Detection")
    jbig2_detected = detect_jbig2(pdf_path)
    if jbig2_detected:
        st.success("✅ JBIG2 Compression Found")
    else:
        st.warning("❌ No JBIG2 Compression Detected")

    # Extract visible text
    st.subheader("📄 Extracted OCR-Visible Text")
    visible_text = extract_visible_text(pdf_path)
    st.text_area("Visible Text", visible_text[:2000], height=300)

    # Extract text from JBIG2 images using OCR
    st.subheader("📜 OCR Extraction from JBIG2 Images")
    ocr_text = extract_text_from_images(pdf_path)
    st.text_area("OCR Extracted Text", ocr_text[:2000], height=300)

    # Extract financial data from both visible and OCR-extracted text
    st.subheader("💰 Extracted Financial & Property Data")
    combined_text = visible_text + "\n" + ocr_text
    financial_data = extract_financial_data(combined_text)
    if financial_data:
        st.json(financial_data)
    else:
        st.warning("❌ No financial data found.")

    os.remove(pdf_path)
