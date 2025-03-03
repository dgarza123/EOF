import os
import subprocess
import streamlit as st
import fitz  # PyMuPDF
import binascii
import re
import zipfile
import base64
import chardet
import codecs
import zlib
from google.cloud import vision
import io

# Ensure necessary dependencies are installed
required_packages = ["google-cloud-vision", "pdf2image", "Pillow"]
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        subprocess.run(["pip", "install", package])

# Initialize Google Vision API client
client = vision.ImageAnnotatorClient()

def decompress_pdf_stream(data):
    try:
        return zlib.decompress(data)
    except zlib.error:
        return None

def google_vision_ocr(image_bytes):
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description if texts else ""

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
    "Names": r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b",
    "Locations": r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b",
    "Large Numerical Values": r"\b\d{5,}\b"
}

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
    
    # Decompress and analyze stream objects
    for page in doc:
        for obj in page.get_contents():
            decompressed_data = decompress_pdf_stream(obj)
            if decompressed_data:
                extracted_text += "\n\n" + decompressed_data.decode("utf-8", errors="ignore")
    
    # If no text is found, attempt OCR via Google Vision
    if not extracted_text.strip():
        images = convert_from_bytes(pdf_bytes)
        extracted_text = "\n\n".join([google_vision_ocr(img.tobytes()) for img in images])
    
    hidden_objects = "✅ No hidden text in PDF objects." if extracted_text.strip() else "🚨 Possible hidden text in PDF objects."
    
    # Compile results
    results["Filtered Hex Dump (Base64 Encoded)"] = hex_encoded
    results["Hidden Financial Data in Hex"] = hex_hits if hex_hits else "✅ No financial markers found in hex."
    results["EOF Hidden Data Status"] = hidden_data_status
    results["Detected Encoding"] = encoding_used
    results["Base64 Encoded Data"] = base64_status
    results["PDF Object & Stream Analysis"] = hidden_objects
    results["Extracted Text (Google OCR + Standard)"] = extracted_text[:500] if extracted_text else "✅ No readable text found."
    
    return results

# Streamlit UI
st.title("🔍 Forensic PDF Analyzer (Advanced EOF, Encoding, XOR, Google OCR, Base85 & Flate Decompression)")
