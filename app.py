import os
import streamlit as st
from google.cloud import vision
from PIL import Image
from io import BytesIO
import fitz  # PyMuPDF
import pandas as pd

# Access Google Vision credentials from Streamlit secrets (set in Streamlit Cloud)
google_vision_credentials_path = st.secrets["google_vision"]["credentials_path"]

# Set the environment variable for Google Vision API authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_vision_credentials_path

# Initialize Google Vision client
client = vision.ImageAnnotatorClient()

# Function to perform OCR using Google Vision
def extract_text_from_image_with_vision(image_data):
    image = vision.Image(content=image_data)
    response = client.text_detection(image=image)
    
    # Extract text from the response
    if response.error.message:
        raise Exception(f"Google Vision API Error: {response.error.message}")
    else:
        texts = response.text_annotations
        return texts[0].description if texts else ""  # Return the full detected text

# Function to extract text from PDF using images and Google Vision OCR
def extract_graphics_as_images_for_ocr(pdf_path):
    doc = fitz.open(pdf_path)
    ocr_texts = []

    for page in doc:
        images = page.get_images(full=True)  # Extract images from the page
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_data = base_image["image"]
            
            # Apply OCR using Google Vision on the extracted image
            ocr_result = extract_text_from_image_with_vision(image_data)
            if ocr_result.strip():
                ocr_texts.append(f"Page {page.number + 1}, Image {img_index}: {ocr_result}")

    return ocr_texts

# Function to extract PDF metadata
def detect_pdf_metadata(pdf_path):
    doc = fitz.open(pdf_path)
    metadata = doc.metadata
    return metadata

# Main function to extract data from PDF
def extract_data_from_pdf(pdf_path):
    ocr_text = extract_graphics_as_images_for_ocr(pdf_path)  # Extract OCR text from images using Google Vision
    metadata = detect_pdf_metadata(pdf_path)  # Extract metadata for extra details
    
    # Combine all extracted data
    return {
        "OCR Text": ocr_text,
        "Metadata": metadata
    }

# Streamlit user interface
st.title("PDF Data Extractor with Google Vision OCR")
st.sidebar.header("Upload Your PDF")

# Upload PDF
uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.write("Processing the file...")

    # Extract the necessary data from the uploaded PDF
    extracted_data = extract_data_from_pdf(uploaded_file)

    # Display extracted data
    st.subheader("OCR Extracted Text from Images using Google Vision")
    st.write(extracted_data["OCR Text"])

    st.subheader("PDF Metadata")
    st.write(extracted_data["Metadata"])
