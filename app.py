import streamlit as st
import fitz  # PyMuPDF
import binascii
import re
import os
import zipfile
from io import BytesIO
import base64
import chardet
import codecs
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

def xor_decrypt(data, key):
    return bytes([b ^ key for b in data])

# Define regex patterns for forensic markers
patterns = {
    "T-Numbers": r"\bT-?\d{6,9}\b",
    "Certificate of Title Numbers": r"Certificate\s*No[:.\s]*\d{6,9}",
    "APN": r"\b\d{3}[-\s]?\d{2,3}[-\s]?\d{2,3}\b",
    "Monetary Values": r"[$€¥£]?\d{1,3}(?:[.,]?\d{3})*(?:\.\d{1,2})?\s?[MBK]?\b",
    "Document Dates": r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b",
    "Unix Timestamps": r"\b\d{10}\b",
    "Names": r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b",  # Detects Firstname Lastname patterns
    "Locations": r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b",  # General location pattern
    "Large Numerical Values": r"\b\d{5,}\b"  # Detects large numbers (possible transactions)
}

# Function to analyze a PDF for hidden data
def analyze_pdf(file):
    results = {}
    pdf_bytes = file.read()
    
    # Open PDF with PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # Read hex data and extract printable ASCII characters
    hex_data = binascii.hexlify(pdf_bytes[:50000]).decode("utf-8").lower()  # Limit extraction to 50KB
    printable_text = ''.join(chr(int(hex_data[i:i+2], 16)) for i in range(0, len(hex_data), 2) if int(hex_data[i:i+2], 16) in range(32, 127))
    
    # Encode hex dump to avoid system security flags
    hex_encoded = base64.b64encode(printable_text.encode()).decode()
    
    # Search for forensic markers in hex
    hex_hits = {}
    for label, pattern in patterns.items():
        matches = re.findall(pattern, printable_text)
        if matches:
            hex_hits[label] = list(set(matches))
    
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
    
    # If no text is found, attempt OCR
    if not extracted_text.strip():
        images = convert_from_bytes(pdf_bytes)
        extracted_text = "\n\n".join([pytesseract.image_to_string(img) for img in images])
    
    hidden_objects = "✅ No hidden text in PDF objects." if extracted_text.strip() else "🚨 Possible hidden text in PDF objects."
    
    # Compile results
    results["Filtered Hex Dump (Base64 Encoded)"] = hex_encoded
    results["Hidden Financial Data in Hex"] = hex_hits if hex_hits else "✅ No financial markers found in hex."
    results["EOF Hidden Data Status"] = hidden_data_status
    results["Detected Encoding"] = encoding_used
    results["Base64 Encoded Data"] = base64_status
    results["PDF Object & Stream Analysis"] = hidden_objects
    results["Extracted Text (OCR + Standard)"] = extracted_text[:500] if extracted_text else "✅ No readable text found."
    
    return results

# Streamlit UI
st.title("🔍 Forensic PDF Analyzer (Advanced EOF, Encoding, XOR, OCR & Hex Dump Analysis)")

uploaded_files = st.file_uploader("Upload PDFs for analysis", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    all_results = {}
    
    for uploaded_file in uploaded_files:
        with st.spinner(f"Analyzing {uploaded_file.name}..."):
            results = analyze_pdf(uploaded_file)
            all_results[uploaded_file.name] = results
    
    # Display results
    for filename, data in all_results.items():
        st.subheader(f"Results for {filename}")
        for key, value in data.items():
            st.write(f"**{key}:** {value}")
    
    # Allow user to download results
    with zipfile.ZipFile("forensic_results.zip", "w") as zipf:
        for filename, data in all_results.items():
            report_text = "\n".join([f"{key}: {value}" for key, value in data.items()])
            zipf.writestr(f"{filename}_report.txt", report_text)
    
    with open("forensic_results.zip", "rb") as f:
        st.download_button("📥 Download Full Forensic Report", f, file_name="forensic_results.zip", mime="application/zip")
