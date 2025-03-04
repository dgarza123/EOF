import os
import json
import base64
import requests
import streamlit as st
import fitz  # PyMuPDF

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

    # Convert first page to an image
    page = doc[0]
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

    # Extract and display text
    if "responses" in result and "textAnnotations" in result["responses"][0]:
        extracted_text = result["responses"][0]["textAnnotations"][0]["description"]
        return extracted_text
    else:
        return "🚨 No text detected."

# Streamlit UI
st.title("🔍 Forensic PDF Analyzer (Google Vision OCR)")

# File Upload
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

if uploaded_file:
    st.write("📄 Processing file:", uploaded_file.name)
    extracted_text = google_vision_ocr(uploaded_file)

    # Display extracted text
    if extracted_text:
        st.subheader("📝 Extracted Text")
        st.text_area("OCR Result", extracted_text, height=200)
    else:
        st.error("🚨 No text detected in the document.")
