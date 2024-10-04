import pytesseract
from pdf2image import convert_from_path
import re
from PyPDF2 import PdfReader

# Path to the Tesseract executable on Windows (if needed)
# Uncomment if you're using Windows:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def pdf_to_text(pdf_path, page=None, n=1):
    """
    Converts a PDF file into text using Tesseract OCR, limiting the number of pages
    to process based on a central page (defined by 'page') and a number of pages before and after ('n').

    Args:
        pdf_path (str): Path to the PDF to convert.
        page (int, optional): Number of the central page to process. If None, the entire PDF is processed.
        n (int): The number of pages before and after the 'page' to analyze.

    Returns:
        str: The extracted text.
    """

    # Get total number of pages in the PDF
    with open(pdf_path, "rb") as file:
        pdf_reader = PdfReader(file)  # Cambia PdfFileReader por PdfReader
        total_pages = len(pdf_reader.pages)
    
    print(f"PDF has {total_pages} pages.")

    # Determine the range of pages to process (if a specific central page is defined)
    if page is not None:
        # Ensure that `page` is within the allowed range
        page = max(1, min(page, total_pages))  # Adjust if the requested page is out of range

        if n == 0:
            # Process only the target page
            start_page = page
            end_page = page
        else:
            # Calculate the range of pages to process with `n` pages before and after
            start_page = max(1, page - n)  # Ensure it doesn't go below page 1
            end_page = min(total_pages, page + n)  # Ensure it doesn't exceed the total number of pages

        print(f"Processing from page {start_page} to {end_page}...")

        # Convert only the needed pages to images
        page_numbers = list(range(start_page - 1, end_page))  # Convert to zero-based index for pdf2image
        pages_to_process = convert_from_path(pdf_path, first_page=start_page, last_page=end_page)
    else:
        # Process the entire PDF
        print("Processing all pages of the PDF...")
        page_numbers = list(range(total_pages))  # All pages from 0 to total_pages - 1
        pages_to_process = convert_from_path(pdf_path)

    # Initialize a string to store all the extracted text from the PDF
    pdf_text = ""

    # Process the selected pages
    for page_num, page_image in zip(page_numbers, pages_to_process):
        print(f"Processing page {page_num + 1} of {total_pages}...")  # Output 1-based page number
        
        # Extract the text using Tesseract
        page_text = pytesseract.image_to_string(page_image)

        # Append the text from this page to the accumulator
        pdf_text += page_text + "\n\n"

    # Post-processing: reduce multiple consecutive newlines to just two newlines
    pdf_text = re.sub(r'\s*\n\s*\n\s*\n+', '\n\n', pdf_text)

    return pdf_text


# Usage example
if __name__ == "__main__":
    # Path to the PDF file
    pdf_path = "/home/andromedalactea/freelance/AI_APEC_Develop/data/Books-20240918T233426Z-001/Books/Lucy-Ann McFadden Editor, Paul Weissman Editor,.pdf"
    
    # Page to process (you can change this)
    target_page = 900  # Target (central) page
    n_range = 1  # Number of pages before and after

    # Call the function to convert the PDF to text from `target_page` with `n_range`
    print(pdf_to_text(pdf_path, page=target_page, n=n_range))