import pytesseract
from pdf2image import convert_from_path
import re

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
        output_txt (str): The file where the extracted text will be saved.

    Returns:
        None: The extracted text is saved in an output file.
    """
    # Convert the PDF to images
    print(f"Converting PDF ({pdf_path}) to images...")
    pages = convert_from_path(pdf_path)

    total_pages = len(pages)  # Total number of pages in the PDF
    print(f"PDF has {total_pages} pages.")

    # Initialize a string to store all the extracted text from the PDF
    pdf_text = ""

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
        pages_to_process = pages[start_page-1:end_page]  # Subset of pages to process
    else:
        # If no specific page is provided, process the entire PDF
        print("Processing all pages of the PDF...")
        pages_to_process = pages

    # Process the selected pages
    for page_num, page_image in enumerate(pages_to_process, start=start_page if page else 1):
        print(f"Processing page {page_num} of {total_pages}...")
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
    pdf_path = "/home/andromedalactea/freelance/AI_APEC_Develop/data/pdf2/577013-764.pdf"
    
    # Page to process (you can change this)
    target_page = 5  # Target (central) page
    n_range = 1  # Number of pages before and after

    # Call the function to convert the PDF to text from `target_page` with `n_range`
    pdf_to_text(pdf_path, page=target_page, n=n_range)