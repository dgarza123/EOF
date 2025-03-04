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

def xor_decrypt(data, key):
    return bytes([b ^ key for b in data])

def brute_force_xor(pdf_bytes):
    results = {}
    for key in range(1, 256):  # Test all byte values as keys
        try:
            decrypted = xor_decrypt(pdf_bytes, key).decode("utf-8", errors="ignore")
            if decrypted.strip():
                results[f"Key {key}"] = decrypted[:500]  # Limit displayed output
        except:
            continue
    return results if results else "✅ No XOR-encoded data found."

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

def attempt_alternative_decoding(data):
    results = {}
    try:
        decoded_base85 = base64.a85decode(data, adobe=True).decode("utf-8", errors="ignore")
        results["Base85"] = "🚨 Hidden text found!" if decoded_base85.strip() else "✅ No hidden text."
    except:
        results["Base85"] = "✅ No Base85 encoded data found."

    try:
        decoded_qp = quopri.decodestring(data).decode("utf-8", errors="ignore")
        results["Quoted-Printable"] = "🚨 Hidden text found!" if decoded_qp.strip() else "✅ No hidden text."
    except:
        results["Quoted-Printable"] = "✅ No Quoted-Printable encoded data found."
    return results

def force_ocr_on_pdf(pdf_bytes):
    images = convert_from_bytes(pdf_bytes)
    extracted_text = ""
    for img in images:
        extracted_text += pytesseract.image_to_string(img) + "\n\n"
    return extracted_text if extracted_text.strip() else "✅ No additional text detected via OCR."

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
    alternative_decodings = attempt_alternative_decoding(pdf_bytes)
    extracted_objects = extract_pdf_objects(doc)
    ocr_text = force_ocr_on_pdf(pdf_bytes)
    xor_results = brute_force_xor(pdf_bytes)

    results["Filtered Hex Dump"] = hex_data[:1000] + "..."
    results["EOF Hidden Data Status"] = hidden_data_status
    results["Detected Encoding"] = encoding_used
    results["Alternative Encoding Analysis"] = alternative_decodings
    results["Extracted PDF Objects"] = extracted_objects
    results["OCR Extracted Text"] = ocr_text
    results["XOR Decryption Attempts"] = xor_results
    return results

st.title("🔍 Forensic PDF Analyzer (Google Vision OCR & Advanced Hidden Data Analysis)")

uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

if uploaded_file:
    st.write("📄 Processing file:", uploaded_file.name)
    forensic_results = analyze_pdf(uploaded_file)

    st.subheader("🔍 Forensic PDF Analysis")
    for key, value in forensic_results.items():
        st.write(f"**{key}:** {value}")
