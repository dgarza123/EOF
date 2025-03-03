import os
import subprocess

# Ensure necessary dependencies are installed
required_packages = ["pytesseract", "pdf2image", "Pillow"]

for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        subprocess.run(["pip", "install", package])

# Ensure Tesseract OCR is installed
if not os.path.exists("/usr/bin/tesseract"):
    subprocess.run(["sudo", "apt-get", "install", "-y", "tesseract-ocr"])

import pytesseract  # Now it should work!
