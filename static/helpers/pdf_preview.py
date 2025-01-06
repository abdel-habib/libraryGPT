import fitz
from PIL import Image
import io
import base64

def get_pdf_preview(pdf_path):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    
    # Get the first page
    first_page = pdf_document.load_page(0)
    
    # Render the page as a pixmap
    pix = first_page.get_pixmap()
    
    # Convert pixmap to PIL Image
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    # Create a byte stream to hold the image data
    img_byte_arr = io.BytesIO()
    
    # Save the image to the byte stream in PNG format
    img.save(img_byte_arr, format='PNG')
    
    # Get the byte string from the stream
    img_byte_arr = img_byte_arr.getvalue()
    
    # Close the PDF document
    pdf_document.close()
    
    return img_byte_arr

def get_pdf_preview_with_crop(pdf_path, size=600):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)
    
    # Get the first page
    first_page = pdf_document.load_page(0)
    
    # Get the page dimensions
    page_rect = first_page.rect
    
    # Calculate the crop box for a square area at the top of the page
    crop_size = min(page_rect.width, page_rect.height, size)
    crop_box = fitz.Rect(0, 0, crop_size, crop_size)
    
    # Render the cropped area as a pixmap
    pix = first_page.get_pixmap(matrix=fitz.Matrix(1, 1), clip=crop_box)
    
    # Convert pixmap to PIL Image
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    # Resize the image to the desired size
    img = img.resize((size, size), Image.LANCZOS)
    
    # Create a byte stream to hold the image data
    img_byte_arr = io.BytesIO()
    
    # Save the image to the byte stream in PNG format
    img.save(img_byte_arr, format='PNG')
    
    # Get the byte string from the stream
    img_byte_arr = img_byte_arr.getvalue()
    
    # Close the PDF document
    pdf_document.close()
    
    return img_byte_arr

def return_pdf_preview_html(pdf_path, crop=False, size=600):
    # Get the preview image as bytes
    preview_bytes = get_pdf_preview_with_crop(pdf_path, size) if crop else get_pdf_preview(pdf_path)
    
    # Encode the bytes to base64
    base64_encoded = base64.b64encode(preview_bytes).decode('utf-8')
    
    # Create the data URL
    data_url = f"data:image/png;base64,{base64_encoded}"
    
    return data_url
