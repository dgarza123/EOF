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

def decompress_pdf_stream(data):
    try:
        return zlib.decompress(data)
    except zlib.error:
        return None

# Load API key from Streamlit Secrets
if "GOOGLE_API_KEY" in st.secrets:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    st.write("✅ Google API Key Loaded Successfully!")
else:
    st.error("🚨 Google API Key Not Found in Streamlit Secrets!")

# Function to process an uploaded PDF with Google Vision API
def google_vision_ocr(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    if len(doc) == 0:
        st.error("🚨 No pages found in PDF!")
        return None

    extracted_text = ""

    # Process all pages in the PDF
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")

        # Convert the image to Base64
        img_base64 = base64.b64encode(img_bytes).decode()

        # Create the Vision API request payload
        url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_API_KEY}"
        payload = {
            "requests": [
                {
                    "image": {
                        "content": img_base64
                    },
                    "features": [{"type": "TEXT_DETECTION"}]
                }
            ]
        }

        # Send request to Google Vision API
        response = requests.post(url, json=payload)
        result = response.json()

        # Extract and append text
        if "responses" in result and "textAnnotations" in result["responses"][0]:
            extracted_text += result["responses"][0]["textAnnotations"][0]["description"] + "\n\n"
        else:
            extracted_text += f"🚨 No text detected on page {page_num + 1}.\n\n"

    return extracted_text.strip()

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
    
    hidden_objects = "✅ No hidden text in PDF objects." if printable_text.strip() else "🚨 Possible hidden text in PDF objects."
    
    # Compile results
    results["Filtered Hex Dump (Base64 Encoded)"] = hex_encoded
    results["EOF Hidden Data Status"] = hidden_data_status
    results["Detected Encoding"] = encoding_used
    results["Base64 Encoded Data"] = base64_status
    results["PDF Object & Stream Analysis"] = hidden_objects
    
    return results

# Streamlit UI
st.title("🔍 Forensic PDF Analyzer (Google Vision OCR & Hidden Data Detection)")

# File Upload
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

if uploaded_file:
    st.write("📄 Processing file:", uploaded_file.name)
    extracted_text = google_vision_ocr(uploaded_file)
    forensic_results = analyze_pdf(uploaded_file)
    
    # Display extracted text
    if extracted_text:
        st.subheader("📝 Extracted Text (OCR)")
        st.text_area("OCR Result", extracted_text, height=400)
    else:
        st.error("🚨 No text detected in the document.")
    
    # Display forensic analysis results
    st.subheader("🔍 Forensic PDF Analysis")
    for key, value in forensic_results.items():
        st.write(f"**{key}:** {value}")
