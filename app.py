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
import base64
import quopri
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import shutil
import re
import codecs

# Ensure pdf2image knows where Poppler is located
PDF2IMAGE_POPPLER_PATH = shutil.which("pdftoppm") or "/usr/bin"

if not PDF2IMAGE_POPPLER_PATH:
    st.error("🚨 Poppler is not installed or not found in PATH. OCR may fail.")

def xor_decrypt(data, key):
    return bytes([b ^ key for b in data])

def filter_xor_results(xor_results):
    filtered_results = {}
    pattern = re.compile(r'\b\d{6,10}\b|\b(?:[A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b')
    for key, value in xor_results.items():
        matches = pattern.findall(value)
        if matches:
            filtered_results[key] = matches[:10]  # Limit output per key
    return filtered_results if filtered_results else "✅ No relevant data found in XOR analysis."

def brute_force_xor(pdf_bytes):
    results = {}
    for key in range(1, 256):  # Test all byte values as keys
        try:
            decrypted = xor_decrypt(pdf_bytes, key).decode("utf-8", errors="ignore")
            if decrypted.strip():
                results[f"Key {key}"] = decrypted
        except:
            continue
    return filter_xor_results(results)

def detect_utf7(data):
    try:
        decoded_text = data.decode("utf-7")
        return decoded_text if decoded_text.strip() else "✅ No UTF-7 encoded text found."
    except:
        return "✅ No UTF-7 encoded text found."

def detect_uuencode(data):
    try:
        decoded_text = codecs.decode(data, "uu").decode("utf-8", errors="ignore")
        return decoded_text if decoded_text.strip() else "✅ No UUEncoded text found."
    except:
        return "✅ No UUEncoded text found."

def detect_rot13(data):
    try:
        decoded_text = codecs.decode(data.decode("utf-8", errors="ignore"), "rot_13")
        return decoded_text if decoded_text.strip() else "✅ No ROT13 encoded text found."
    except:
        return "✅ No ROT13 encoded text found."

def detect_double_base64(data):
    try:
        decoded_once = base64.b64decode(data).decode("utf-8", errors="ignore")
        decoded_twice = base64.b64decode(decoded_once).decode("utf-8", errors="ignore")
        return decoded_twice if decoded_twice.strip() else "✅ No Double Base64 encoded text found."
    except:
        return "✅ No Double Base64 encoded text found."

def extract_pdf_objects(doc):
    extracted_data = ""
    for page in doc:
        for obj in page.get_contents():
            try:
                raw_data = obj.read_bytes()
                try:
                    decompressed_data = zlib.decompress(raw_data).decode("utf-8", errors="ignore")
                    extracted_data += decompressed_data + "\n\n"
                except:
                    extracted_data += raw_data.decode("utf-8", errors="ignore") + "\n\n"
            except:
                continue  # Skip if unreadable
    return extracted_data if extracted_data.strip() else "✅ No additional text found."

def analyze_pdf(file):
    results = {}
    file.seek(0)
    pdf_bytes = file.read()

    if not pdf_bytes:
        st.error("🚨 The uploaded PDF file appears to be empty or corrupted.")
        return results

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        st.error("🚨 Failed to open PDF. The file may be corrupted.")
        return results

    hex_data = binascii.hexlify(pdf_bytes[:50000]).decode("utf-8").lower()
    eof_marker = b"%%EOF"
    eof_index = pdf_bytes.rfind(eof_marker)
    hidden_data = pdf_bytes[eof_index + len(eof_marker):] if eof_index != -1 else None
    hidden_data_status = "✅ No hidden data after EOF." if not hidden_data.strip() else "🚨 Hidden data detected after EOF."
    detected_encoding = chardet.detect(pdf_bytes)
    encoding_used = detected_encoding["encoding"] if detected_encoding["confidence"] > 0.5 else "Unknown"
    extracted_objects = extract_pdf_objects(doc)
    xor_results = brute_force_xor(pdf_bytes)

    additional_decoding = {
        "UTF-7": detect_utf7(pdf_bytes),
        "UUEncode": detect_uuencode(pdf_bytes),
        "ROT13": detect_rot13(pdf_bytes),
        "Double Base64": detect_double_base64(pdf_bytes)
    }

    results["Filtered Hex Dump"] = hex_data[:1000] + "..."
    results["EOF Hidden Data Status"] = hidden_data_status
    results["Detected Encoding"] = encoding_used
    results["Extracted PDF Objects"] = extracted_objects
    results["XOR Decryption Attempts"] = xor_results
    results["Additional Encoding Analysis"] = additional_decoding
    return results

st.title("🔍 Forensic PDF Analyzer (Google Vision OCR & Advanced Hidden Data Analysis)")

uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

if uploaded_file:
    st.write("📄 Processing file:", uploaded_file.name)
    forensic_results = analyze_pdf(uploaded_file)

    st.subheader("🔍 Forensic PDF Analysis")
    for key, value in forensic_results.items():
        st.write(f"**{key}:** {value}")
