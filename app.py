import streamlit as st
import PyPDF2
import pytesseract
import base64
import zlib
import os
import re
from pdf2image import convert_from_path
from io import BytesIO
from PIL import Image
import numpy as np

# Function to extract text using OCR
def extract_text_from_image(image):
    return pytesseract.image_to_string(image, lang="eng")

# Function to detect Base64-encoded hidden data
def detect_base64(text):
    base64_pattern = r"(?:[A-Za-z0-9+/]{4}){2,}(?:[A-Za-z0-9+/=]{2,4})?"
    matches = re.findall(base64_pattern, text)
    decoded_texts = []
    for match in matches:
        try:
            decoded_text = base64.b64decode(match).decode("utf-8", errors="ignore")
            decoded_texts.append(decoded_text)
        except Exception:
            continue
    return decoded_texts

# Function to extract Zlib (FlateDecode) streams
def extract_zlib_stream(pdf_bytes, start_offset, end_offset):
    """Extracts and decompresses a Zlib (FlateDecode) compressed stream from a PDF."""
    try:
        compressed_data = pdf_bytes[start_offset:end_offset]
        decompressed_data = zlib.decompress(compressed_data)
        return decompressed_data.decode("utf-8", errors="ignore")
    except zlib.error as e:
        return f"❌ Failed to decompress Zlib: {str(e)}"

# Function to extract financial & property-related markers
def extract_financial_data(text):
    bank_acc_pattern = r"\b\d{8,12}\b"
    routing_num_pattern = r"\b\d{9}\b"
    credit_card_pattern = r"\b(?:\d[ -]*?){13,16}\b"
    money_pattern = r"\$\d+(?:,\d{3})*(?:\.\d{2})?"

    bank_accounts = re.findall(bank_acc_pattern, text)
    routing_numbers = re.findall(routing_num_pattern, text)
    credit_cards = re.findall(credit_card_pattern, text)
    monetary_values = re.findall(money_pattern, text)

    return {
        "Bank Accounts": bank_accounts,
        "Routing Numbers": routing_numbers,
        "Credit Cards": credit_cards,
        "Monetary Values": monetary_values,
    }

# Streamlit UI
st.title("📜 Shiva PDF Analyzer - Hidden Data Extraction")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file:
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Convert PDF to images
    images = convert_from_path("temp.pdf")

    # Extract OCR text
    extracted_text = ""
    for img in images:
        extracted_text += extract_text_from_image(img) + "\n"

    # Read PDF bytes for deeper analysis
    with open("temp.pdf", "rb") as pdf_file:
        pdf_bytes = pdf_file.read()

    # Extract Zlib (FlateDecode) data
    zlib_output = extract_zlib_stream(pdf_bytes, 0x528, 0x569)  # Adjust offset if needed

    # Detect Base64 hidden content
    base64_data = detect_base64(zlib_output)

    # Extract financial markers
    financial_data = extract_financial_data(zlib_output)

    # Display extracted results
    st.subheader("💰 Extracted Financial & Property Data")
    if any(financial_data.values()):
        st.json(financial_data)
    else:
        st.warning("❌ No financial data found.")

    st.subheader("📜 Base64 Decoded Hidden Data")
    if base64_data:
        st.json(base64_data)
    else:
        st.error("❌ No Base64 encoded hidden data found.")

    st.subheader("🧩 FlateDecode (Zlib) Decompressed Data Preview")
    if "Failed to decompress" in zlib_output:
        st.error(zlib_output)
    else:
        st.code(zlib_output, language="plaintext")

    st.subheader("📄 Extracted OCR-Visible Text")
    if extracted_text.strip():
        st.text(extracted_text[:500])  # Show preview of OCR text
    else:
        st.error("❌ No visible text extracted.")

# Clean up
os.remove("temp.pdf")
