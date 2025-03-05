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
    base64_pattern = re.compile(r"([A-Za-z0-9+/]{30,}={0,2})")
    base64_matches = base64_pattern.findall(text)
    
    decoded_results = []
    for match in base64_matches:
        try:
            decoded_text = base64.b64decode(match).decode("utf-8", errors="ignore")
            if decoded_text.strip():
                decoded_results.append(decoded_text.strip())
        except (binascii.Error, UnicodeDecodeError):
            pass  # Ignore non-decodable values
    
    return decoded_results if decoded_results else ["❌ No valid Base64 data found."]

# Function to decompress FlateDecode (Zlib)
def decompress_flate(hex_data):
    try:
        binary_data = binascii.unhexlify(hex_data)  # Convert hex back to binary
        decompressed_text = zlib.decompress(binary_data).decode("utf-8", errors="ignore").strip()
        return decompressed_text if decompressed_text else "❌ No valid compressed data detected."
    except Exception:
        return "❌ Failed to decompress FlateDecode (Data may be encrypted or invalid)."

# Function to decode UTF-16 LE text
def decode_utf16_le(hex_data):
    try:
        binary_data = binascii.unhexlify(hex_data)
        decoded_text = binary_data.decode("utf-16-le", errors="ignore").strip()
        return decoded_text if decoded_text else "❌ No UTF-16 LE encoded data detected."
    except Exception:
        return "❌ Failed to decode UTF-16 LE (Invalid format)."

# Function to extract financial & property markers
def extract_financial_markers(text):
    patterns = {
        "Bank Accounts": re.compile(r"\b\d{8,12}\b"),  # Matches 8-12 digit bank account numbers
        "Credit Card Numbers": re.compile(r"\b\d{13,16}\b"),  # Matches 13-16 digit credit card numbers
        "Monetary Values": re.compile(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?"),  # Matches monetary values
        "Property IDs": re.compile(r"\bT\s?\d{6}\b"),  # Matches Torrens Title Numbers (T 123456)
    }

    extracted_data = {key: list(set(pattern.findall(text))) for key, pattern in patterns.items()}
    return {k: v for k, v in extracted_data.items() if v}

# If a file is uploaded, process it
if uploaded_file:
    st.write("🔍 Processing the PDF...")

    # Convert PDF to hex
    pdf_hex_data = convert_pdf_to_hex(uploaded_file)

    # Extract Base64 encoded hidden data
    base64_decoded_texts = extract_base64_strings(pdf_hex_data)

    # Attempt FlateDecode (Zlib decompression)
    flate_decoded_text = decompress_flate(pdf_hex_data)

    # Attempt UTF-16 LE decoding
    utf16_decoded_text = decode_utf16_le(pdf_hex_data)

    # Extract financial markers from decoded data
    extracted_financial_data = extract_financial_markers(flate_decoded_text + " " + utf16_decoded_text)

    # Display structured results
    st.subheader("📖 Extracted Financial & Property Data")

    # Convert extracted data to DataFrame
    if extracted_financial_data:
        financial_df = pd.DataFrame.from_dict(extracted_financial_data, orient="index").transpose()
        st.dataframe(financial_df)
    else:
        st.warning("❌ No financial data found.")

    # Display Base64 Decoded Data
    st.subheader("📖 Base64 Decoded Hidden Data")
    st.write(base64_decoded_texts)

    # Display FlateDecode (Zlib) Decompressed Data
    st.subheader("📖 FlateDecode (Zlib) Decompressed Data Preview")
    st.write(flate_decoded_text[:500])  # Show preview of first 500 characters

    # Display UTF-16 LE Decoded Data
    st.subheader("📖 UTF-16 LE Decoded Data Preview")
    st.write(utf16_decoded_text[:500])  # Show preview of first 500 characters
