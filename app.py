import streamlit as st
import fitz  # PyMuPDF
import binascii
import re
import os
import zipfile
from io import BytesIO

# Define regex patterns for financial markers
patterns = {
    "T-Numbers": r"\bT-?\d{6,9}\b",
    "Certificate of Title Numbers": r"Certificate\s*No[:.\s]*\d{6,9}",
    "APN": r"\b\d{3}[-\s]?\d{2,3}[-\s]?\d{2,3}\b",
    "Monetary Values": r"[$€¥£]?\d{1,3}(?:[.,]?\d{3})*(?:\.\d{1,2})?\s?[MBK]?\b",
    "Document Dates": r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b",
    "Unix Timestamps": r"\b\d{10}\b"
}

# Function to analyze a PDF for EOF hidden data
def analyze_pdf(file):
    results = {}
    pdf_bytes = file.read()
    
    # Open PDF with PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # Read hex data
    hex_data = binascii.hexlify(pdf_bytes).decode("utf-8").lower()
    
    # Search for financial markers in hex
    hex_hits = {}
    for label, pattern in patterns.items():
        matches = re.findall(pattern, hex_data)
        if matches:
            hex_hits[label] = list(set(matches))
    
    # Check for EOF anomalies (hidden data after %%EOF)
    eof_marker = b"%%EOF"
    eof_index = pdf_bytes.rfind(eof_marker)
    hidden_data = pdf_bytes[eof_index + len(eof_marker):] if eof_index != -1 else None
    hidden_data_status = "✅ No hidden data after EOF." if not hidden_data.strip() else f"🚨 Hidden data detected after EOF: {hidden_data[:100]}"
    
    # Compile results
    results["Hidden Financial Data in Hex"] = hex_hits if hex_hits else "✅ No financial markers found in hex."
    results["EOF Hidden Data Status"] = hidden_data_status
    
    return results

# Streamlit UI
st.title("🔍 Forensic PDF Analyzer (EOF Analysis)")

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
