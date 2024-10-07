import pytesseract
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
import re
import concurrent.futures
from PIL import ImageOps

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

    # You can configure the OCR based on your needs. Here, use Tesseract's default OCR settings.
    custom_config = r'--oem 3 --psm 3'  # Adjust --psm or --oem if necessary

    # Perform OCR
    page_text = pytesseract.image_to_string(processed_image, config=custom_config)
    return page_text

def pdf_to_text(pdf_path, page=None, n=1, dpi=150, num_workers=None):
    """
    Converts a PDF file into text using Tesseract OCR, limiting the number of pages
    to process based on a central page (defined by 'page') and a number of pages before and after ('n').

    Args:
        pdf_path (str): Path to the PDF to convert.
        page (int, optional): Number of the central page to process. If None, the entire PDF is processed.
        n (int): The number of pages before and after 'page' to analyze.
        dpi (int): DPI (Dots Per Inch) to use when converting PDF pages to images. Lower values can increase speed.
        num_workers (int, optional): Number of worker threads in the ThreadPoolExecutor.

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
        pages_to_process = convert_from_path(pdf_path, first_page=start_page, last_page=end_page, dpi=dpi)
    else:
        print("Processing all pages of the PDF...")
        pages_to_process = convert_from_path(pdf_path, dpi=dpi)

    print(f"Pages to process: {len(pages_to_process)}")

    # Use multithreading to process each page
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        page_texts = list(executor.map(process_single_page, pages_to_process))

    # Join the text extracted from all pages
    pdf_text = "\n\n".join(page_texts)

    # Post-processing: remove excessive newlines
    pdf_text = re.sub(r'\s*\n\s*\n\s*\n+', '\n\n', pdf_text)

    return pdf_text