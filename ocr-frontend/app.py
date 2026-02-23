import streamlit as st
import requests
import io
import fitz  # PyMuPDF for PDF to Image conversion
from docx import Document
from fpdf import FPDF

# -----------------------------
# Configuration
# -----------------------------
FASTAPI_URL = "http://localhost:8000/extract-ocr"

st.set_page_config(
    page_title="Handwritten OCR App",
    page_icon="📝",
    layout="wide"
)

# -----------------------------
# Utility Functions
# -----------------------------
def convert_pdf_to_image(pdf_bytes):
    """Extracts the first page of a PDF and converts it to a JPEG image."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)  # Get the first page
    pix = page.get_pixmap(dpi=150)
    return pix.tobytes("jpeg")

def create_word_file(text):
    """Creates a Word document from text and returns bytes."""
    doc = Document()
    doc.add_heading('Extracted Handwritten Text', 0)
    doc.add_paragraph(text)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def create_pdf_file(text):
    """Creates a PDF document from text and returns bytes."""
    pdf = FPDF()
    pdf.add_page()
    
    # Use built-in helvetica. Note: For complex scripts (like Hindi), 
    # you would need to load a custom Unicode TTF font here.
    pdf.set_font("helvetica", size=12) 
    
    # Handle potentially problematic unicode characters for standard fonts
    safe_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, safe_text)
    
    return bytes(pdf.output())

# -----------------------------
# UI Layout
# -----------------------------
st.title("📝 Handwritten Text OCR Engine")
st.markdown("Upload a handwritten document (Image or PDF). The AI will extract the text, which you can then edit and download.")

# State initialization
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""

# File Uploader Container
uploaded_file = st.file_uploader("Drag and drop or browse for an Image or PDF", type=["png", "jpg", "jpeg", "pdf"])

if uploaded_file is not None:
    # --- UI: Two Column Layout ---
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Document Preview")
        file_bytes = uploaded_file.read()
        
        # Determine file type and handle appropriately
        if uploaded_file.type == "application/pdf":
            st.info("PDF detected. Extracting the first page for OCR...")
            try:
                image_bytes = convert_pdf_to_image(file_bytes)
                st.image(image_bytes, caption="PDF First Page Preview", use_container_width=True)
            except Exception as e:
                st.error(f"Error reading PDF: {e}")
                st.stop()
        else:
            image_bytes = file_bytes
            st.image(image_bytes, caption="Image Preview", use_container_width=True)
        
        # Process Button
        if st.button("🔍 Extract Text", use_container_width=True, type="primary"):
            with st.spinner("Analyzing handwriting... Please wait."):
                try:
                    # Send to FastAPI Backend
                    files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
                    response = requests.post(FASTAPI_URL, files=files)
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.extracted_text = data.get("extracted_text", "")
                        st.success("Extraction Complete!")
                    else:
                        st.error(f"Backend Error {response.status_code}: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("🚨 Could not connect to the FastAPI backend. Is it running on port 8000?")

    with col2:
        st.subheader("Extracted Text")
        # Editable Text Area
        edited_text = st.text_area(
            "Review and edit your text below:",
            value=st.session_state.extracted_text,
            height=400
        )
        
        # Download Options (only show if there is text)
        if edited_text:
            st.markdown("### 💾 Download Results")
            d_col1, d_col2, d_col3 = st.columns(3)
            
            with d_col1:
                # 1. TXT Download
                st.download_button(
                    label="📄 Download TXT",
                    data=edited_text,
                    file_name="extracted_text.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
            with d_col2:
                # 2. Word Download
                word_data = create_word_file(edited_text)
                st.download_button(
                    label="📝 Download Word",
                    data=word_data,
                    file_name="extracted_text.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
                
            with d_col3:
                # 3. PDF Download
                pdf_data = create_pdf_file(edited_text)
                st.download_button(
                    label="📕 Download PDF",
                    data=pdf_data,
                    file_name="extracted_text.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )