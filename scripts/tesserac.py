import pytesseract
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
import re
import multiprocessing
from PIL import ImageOps

# Ajusta el comando de Tesseract si estás en Windows:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image):
    """
    Preprocess the image to improve OCR performance. 
    This version converts the image to grayscale.
    """
    return ImageOps.grayscale(image)

def process_single_page(page_image):
    """
    Extracts text from a single image using Tesseract OCR after preprocessing.
    """
    # Preprocess the image (convert to grayscale)
    processed_image = preprocess_image(page_image)
    
    # You can configure the OCR based on your needs. Here, use Tesseract's default "legacy" OCR.
    custom_config = r'--oem 3 --psm 3'  # Can adjust --psm or --oem if necessary
    
    # Perform OCR
    page_text = pytesseract.image_to_string(processed_image, config=custom_config)
    return page_text

def pdf_to_text(pdf_path, page=None, n=1, dpi=150):
    """
    Converts a PDF file into text using Tesseract OCR, limiting the number of pages
    to process based on a central page (defined by 'page') and a number of pages before and after ('n').

    Args:
        pdf_path (str): Path to the PDF to convert.
        page (int, optional): Number of the central page to process. If None, the entire PDF is processed.
        n (int): The number of pages before and after 'page' to analyze.
        dpi (int): DPI (Dots Per Inch) to use when converting PDF pages to images. Lower values can increase speed.

    Returns:
        str: The extracted text.
    """

    # Get total number of pages in the PDF
    with open(pdf_path, "rb") as file:
        pdf_reader = PdfReader(file)
        total_pages = len(pdf_reader.pages)

    print(f"PDF has {total_pages} pages.")

    # Determine the range of pages to process (if a specific central page is defined)
    if page is not None:
        page = max(1, min(page, total_pages))  # Ensure the requested page is in the correct range

        if n == 0:
            start_page, end_page = page, page
        else:
            start_page = max(1, page - n)
            end_page = min(total_pages, page + n)

        print(f"Processing from page {start_page} to {end_page}...")

        # Convert only the needed pages to images
        page_numbers = list(range(start_page - 1, end_page))
        pages_to_process = convert_from_path(pdf_path, first_page=start_page, last_page=end_page, dpi=dpi)
    else:
        print("Processing all pages of the PDF...")
        page_numbers = list(range(total_pages))
        pages_to_process = convert_from_path(pdf_path, dpi=dpi)

    print(f"Pages to process: {len(pages_to_process)}")

    # Multiprocessing to handle multiple pages in parallel
    with multiprocessing.Pool() as pool:
        page_texts = pool.map(process_single_page, pages_to_process)

    # Join the text extracted from all pages
    pdf_text = "\n\n".join(page_texts)

    # Post-processing: remove excessive newlines
    pdf_text = re.sub(r'\s*\n\s*\n\s*\n+', '\n\n', pdf_text)

    return pdf_text


if __name__ == "__main__":
    import time

    # Path to the PDF file
    pdf_path = "/home/andromedalactea/freelance/AI_APEC_Develop/data/Books-20240918T233426Z-001/Books/Lucy-Ann McFadden Editor, Paul Weissman Editor,.pdf"
    
    # Page to process (you can change this)
    target_page = 900  # Target (central) page
    n_range = 1  # Number of pages before and after
    dpi = 150  # Reduce DPI for faster conversion

    # Call the function to convert the PDF to text
    start_time = time.time()
    text= pdf_to_text(pdf_path, page=target_page, n=n_range, dpi=dpi)
    print(text)
    print(len(text))
    end_time = time.time()

    print(f"Time elapsed: {end_time - start_time:.2f} seconds")