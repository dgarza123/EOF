import streamlit as st
import pandas as pd
import base64
import zlib
import re
from PyPDF2 import PdfReader

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    pdf_reader = PdfReader(pdf_file)
    extracted_text = ''
    for page in pdf_reader.pages:
        extracted_text += page.extract_text() or ''
    return extracted_text

# Function to detect Base64 encoded data and decode it
def decode_base64(encoded_text):
    try:
        decoded_bytes = base64.b64decode(encoded_text, validate=True)
        decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
        return decoded_text
    except Exception:
        return None

# Function to attempt zlib decompression
def decompress_zlib(data):
    try:
        decompressed_bytes = zlib.decompress(data)
        return decompressed_bytes.decode('utf-8', errors='ignore')
    except Exception:
        return None

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
st.title("Shiva PDF Analyzer")

uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

if uploaded_file:
    st.subheader("Processing the PDF...")
    
    # Extract visible text
    extracted_text = extract_text_from_pdf(uploaded_file)

    # Display extracted financial data
    financial_data = extract_financial_data(extracted_text)
    st.subheader("📄 Extracted Financial & Property Data")
    if financial_data:
        st.dataframe(pd.DataFrame(dict([(k, pd.Series(v)) for k, v in financial_data.items()])))
    else:
        st.warning("❌ No financial data found.")

    # Attempt to decode Base64 hidden data
    base64_decoded_text = decode_base64(extracted_text)
    st.subheader("📜 Base64 Decoded Hidden Data")
    if base64_decoded_text:
        st.text_area("Decoded Base64 Content", base64_decoded_text, height=200)
    else:
        st.error("❌ No Base64 encoded hidden data found.")

    # Attempt FlateDecode (Zlib Decompression)
    st.subheader("🔍 FlateDecode (Zlib) Decompressed Data Preview")
    zlib_decoded_text = decompress_zlib(extracted_text.encode('utf-8', errors='ignore'))
    if zlib_decoded_text:
        st.text_area("Zlib Decompressed Content", zlib_decoded_text, height=200)
    else:
        st.error("❌ Failed to decompress FlateDecode (Data may be encrypted or invalid).")

    # Display raw extracted text preview
    st.subheader("📑 UTF-16 LE Decoded Data Preview")
    try:
        utf16_text = extracted_text.encode("utf-8").decode("utf-16-le")
        st.text_area("UTF-16 LE Decoded Content", utf16_text, height=200)
    except Exception:
        st.error("❌ Failed to decode UTF-16 LE text.")

st.sidebar.info("Upload a PDF to analyze hidden and financial data.")
