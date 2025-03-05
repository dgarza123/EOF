import streamlit as st
import fitz  # PyMuPDF
import base64
import binascii
import re
import zlib
import pandas as pd

# Title of the app
st.title("📄 Shiva PDF Forensic Analyzer")

# File uploader
uploaded_file = st.file_uploader("Upload a PDF for forensic analysis", type=["pdf"])

# Function to extract and convert PDF to hex
def convert_pdf_to_hex(pdf_file):
    pdf_bytes = pdf_file.read()
    hex_data = binascii.hexlify(pdf_bytes).decode("utf-8")
    return hex_data

# Function to extract Base64 encoded data
def extract_base64_strings(text):
    base64_pattern = re.compile(r"(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?")
    base64_matches = base64_pattern.findall(text)
    decoded_results = []
    for match in base64_matches:
        try:
            decoded_text = base64.b64decode(match).decode("utf-8", errors="ignore")
            decoded_results.append(decoded_text)
        except binascii.Error:
            pass  # Ignore non-decodable values
    return decoded_results

# Function to decompress FlateDecode streams
def decompress_flate(hex_data):
    try:
        binary_data = binascii.unhexlify(hex_data)  # Convert hex back to binary
        decompressed_text = zlib.decompress(binary_data).decode("utf-8", errors="ignore")
        return decompressed_text
    except Exception as e:
        return f"Failed to decompress FlateDecode: {str(e)}"

# Function to decode UTF-16 LE text
def decode_utf16_le(hex_data):
    try:
        binary_data = binascii.unhexlify(hex_data)  # Convert hex back to binary
        decoded_text = binary_data.decode("utf-16-le", errors="ignore")  # Decode as UTF-16 LE
        return decoded_text
    except Exception as e:
        return f"Failed to decode UTF-16 LE: {str(e)}"

# If a file is uploaded, process it
if uploaded_file:
    st.write("🔍 Processing the PDF...")

    # Convert PDF to hex
    pdf_hex_data = convert_pdf_to_hex(uploaded_file)

    # Extract Base64 encoded hidden data
    base64_decoded_texts = extract_base64_strings(pdf_hex_data)

    # Attempt FlateDecode (zlib decompression)
    flate_decoded_texts = decompress_flate(pdf_hex_data)

    # Attempt UTF-16 LE decoding
    utf16_decoded_texts = decode_utf16_le(pdf_hex_data)

    # Display results
    st.subheader("📖 Base64 Decoded Hidden Data")
    st.write(base64_decoded_texts if base64_decoded_texts else "❌ No Base64 encoded data detected.")

    st.subheader("📖 FlateDecode (Zlib) Decompressed Data")
    st.write(flate_decoded_texts if "Failed" not in flate_decoded_texts else "❌ No valid compressed data detected.")

    st.subheader("📖 UTF-16 LE Decoded Data")
    st.write(utf16_decoded_texts if "Failed" not in utf16_decoded_texts else "❌ No UTF-16 LE encoded data detected.")
