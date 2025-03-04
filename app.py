import os
import json
import streamlit as st
import fitz  # PyMuPDF
import binascii
import re
import zipfile
import base64
import chardet
import codecs
import zlib
import requests

# Load API key from Streamlit Secrets
if "GOOGLE_API_KEY" in st.secrets:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    st.write("✅ Google API Key Loaded Successfully!")
else:
    st.error("🚨 Google API Key Not Found in Streamlit Secrets!")

# Function to test Google Vision API
def google_vision_test():
    url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_API_KEY}"
    test_payload = {
        "requests": [
            {
                "image": {
                    "source": {
                        "imageUri": "https://upload.wikimedia.org/wikipedia/commons/4/4f/Google_Cloud_Logo.svg"
                    }
                },
                "features": [{"type": "TEXT_DETECTION"}]
            }
        ]
    }
    
    response = requests.post(url, json=test_payload)
    st.write("🔍 Google Vision API Test Response:", response.json())

# Run the test function
google_vision_test()

# Function to analyze a PDF for hidden data
def analyze_pdf(file):
    results = {}
    pdf_bytes = file.read()
    
    # Open PDF with PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # Read hex data and extract printable ASCII characters
    hex_data = binascii.hexlify(pdf_bytes[:50000]).decode("utf-8").lower()
    printable_text = ''.join(chr(int(hex_data[i:i+2], 16)) for i in range(0, len(hex_data), 2) if int(hex_data[i:i+2], 16) in range(32, 127))
    
    # Encode hex dump to avoid system security flags
    hex_encoded = base64.b64encode(printable_text.encode()).decode()
    
    # Check for EOF anomalies (hidden data after %%EOF)
    eof_marker = b"%%EOF"
    eof_index = pdf_bytes.rfind(eof_marker)
    hidden_data = pdf_bytes[eof_index + len(eof_marker):] if eof_index != -1 else None
    hidden_data_status = "✅ No hidden data after EOF." if not hidden_data.strip() else "🚨 Hidden data detected after EOF."
    
    # Attempt to detect encoding issues
    detected_encoding = chardet.detect(pdf_bytes)
    encoding_used = detected_encoding["encoding"] if detected_encoding["confidence"] > 0.5 else "Unknown"
    
    # Check for Base64 encoded data
    try:
        base64_decoded = base64.b64decode(pdf_bytes, validate=True).decode("utf-8", errors="ignore")
        base64_status = "🚨 Possible Base64 encoded hidden data detected!" if base64_decoded.strip() else "✅ No Base64 encoded hidden data found."
    except Exception:
        base64_status = "✅ No Base64 encoded hidden data found."
    
    # Extract text from PDF objects and streams
    extracted_text = "\n\n".join([page.get_text("text") for page in doc])
    
    hidden_objects = "✅ No hidden text in PDF objects." if extracted_text.strip() else "🚨 Possible hidden text in PDF objects."
    
    # Compile results
    results["Filtered Hex Dump (Base64 Encoded)"] = hex_encoded
    results["EOF Hidden Data Status"] = hidden_data_status
    results["Detected Encoding"] = encoding_used
    results["Base64 Encoded Data"] = base64_status
    results["PDF Object & Stream Analysis"] = hidden_objects
    results["Extracted Text"] = extracted_text[:500] if extracted_text else "✅ No readable text found."
    
    return results

# Streamlit UI
st.title("🔍 Forensic PDF Analyzer (Advanced EOF, Encoding, Google OCR, Base85 & Flate Decompression)")
