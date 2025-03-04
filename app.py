import os
import json
import base64
import requests
import streamlit as st
import fitz  # PyMuPDF
import binascii
import chardet
import codecs
import zlib
from pdf2image import convert_from_bytes
from PIL import Image
import re

# Load API key from Streamlit Secrets
if "GOOGLE_API_KEY" in st.secrets:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    st.write("✅ Google API Key Loaded Successfully!")
else:
    st.error("🚨 Google API Key Not Found in Streamlit Secrets!")

# Function to analyze a PDF for hidden data
def analyze_pdf(file):
    results = {}
    file.seek(0)  # Reset file pointer before reading
    pdf_bytes = file.read()

    # Check if the file is empty
    if not pdf_bytes:
        st.error("🚨 The uploaded PDF file appears to be empty or corrupted.")
        return results

    # Open PDF with PyMuPDF
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        st.error("🚨 Failed to open PDF. The file may be corrupted.")
        return results

    # Read hex data beyond 50,000 bytes (now analyzing full file in chunks)
    chunk_size = 50000
    hex_data_chunks = []
    for i in range(0, len(pdf_bytes), chunk_size):
        hex_data_chunks.append(binascii.hexlify(pdf_bytes[i:i+chunk_size]).decode("utf-8").lower())

    # Search for financial markers in hex data
    financial_patterns = {
        "Bank Account Numbers": r"\b\d{8,12}\b",
        "Routing Numbers": r"\b\d{9}\b",
        "Credit Card Numbers": r"\b(?:\d[ -]*?){13,16}\b",
        "Monetary Values": r"[$€¥£]?\d{1,3}(?:[.,]?\d{3})*(?:\.\d{1,2})?\s?[MBK]?\b"
    }
    financial_hits = {}

    for label, pattern in financial_patterns.items():
        for hex_chunk in hex_data_chunks:
            matches = binascii.unhexlify(hex_chunk).decode("utf-8", errors="ignore")
            detected = list(set(re.findall(pattern, matches)))
            if detected:
                financial_hits[label] = detected

    financial_data_status = "✅ No financial markers found in hex." if not financial_hits else f"🚨 Financial markers detected: {financial_hits}" 

    # Check for EOF anomalies (hidden data after %%EOF)
    eof_marker = b"%%EOF"
    eof_index = pdf_bytes.rfind(eof_marker)
    hidden_data = pdf_bytes[eof_index + len(eof_marker):] if eof_index != -1 else None
    hidden_data_status = "✅ No hidden data after EOF." if not hidden_data.strip() else f"🚨 Hidden data detected after EOF: {hidden_data[:500].decode(errors='ignore')}"

    # Attempt to detect encoding issues
    detected_encoding = chardet.detect(pdf_bytes)
    encoding_used = detected_encoding["encoding"] if detected_encoding["confidence"] > 0.5 else "Unknown"

    # Check for Base64, Base65, and UTF-16 encoded data
    encoding_checks = {
        "Base64": base64.b64decode,
        "Base65": lambda data: base64.b64decode(data.replace("-", "+").replace("_", "/")),
        "UTF-16": lambda data: data.decode("utf-16", errors="ignore")
    }
    encoded_results = {}
    
    for encoding, decoder in encoding_checks.items():
        try:
            decoded = decoder(pdf_bytes).decode("utf-8", errors="ignore")
            encoded_results[encoding] = f"🚨 Hidden data detected! {decoded[:500]}" if decoded.strip() else "✅ No hidden data."
        except Exception:
            encoded_results[encoding] = "✅ No hidden data."
    
    # Compile results
    results["Hex Data Analyzed in Chunks"] = hex_data_chunks[:2]  # Show only first two chunks for performance
    results["Financial Data Status"] = financial_data_status
    results["EOF Hidden Data Status"] = hidden_data_status
    results["Detected Encoding"] = encoding_used
    results["Encoding Analysis"] = encoded_results

    return results

# Streamlit UI
st.title("🔍 Forensic PDF Analyzer (Financial & Hex Analysis)")

# File Upload
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

if uploaded_file:
    st.write("📄 Processing file:", uploaded_file.name)
    forensic_results = analyze_pdf(uploaded_file)
    
    # Display forensic analysis results
    st.subheader("🔍 Forensic PDF Analysis")
    for key, value in forensic_results.items():
        st.write(f"**{key}:** {value}")
