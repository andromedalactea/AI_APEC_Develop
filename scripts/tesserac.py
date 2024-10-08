import os
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
import re
import multiprocessing
from PIL import ImageOps
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

# Load environment variables for Azure Vision credentials
load_dotenv(override=True)
try:
    endpoint = os.environ["VISION_ENDPOINT"]
    key = os.environ["VISION_KEY"]
except KeyError:
    print("Missing environment variable 'VISION_ENDPOINT' or 'VISION_KEY'")
    print("Set them before running this sample.")
    exit()

# Create a global ImageAnalysisClient for Azure OCR
client = ImageAnalysisClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)

def preprocess_image(image):
    """
    Preprocess the image by converting it to grayscale.
    """
    return ImageOps.grayscale(image)

def process_single_page_with_azure(page_image):
    """
    Process a single PDF page using Azure Vision OCR.
    Extract and return the recognized text from the image.
    """
    # Preprocess image to grayscale
    processed_image = preprocess_image(page_image)

    # Convert PIL image to byte array
    from io import BytesIO
    img_byte_array = BytesIO()
    processed_image.save(img_byte_array, format='PNG')
    img_byte_array = img_byte_array.getvalue()

    # Call Azure vision API for OCR
    result = client.analyze(
        image_data=img_byte_array,
        visual_features=["Read"]  # Especificamos que queremos usar solo las características de OCR (lectura de texto)
    )

    extracted_text = ""
    if result.read is not None:
        for line in result.read.blocks[0].lines:
            extracted_text += line.text + "\n"  # Acumular las líneas de texto reconocidas

    return extracted_text

def pdf_to_text(pdf_path, page=None, n=1, dpi=150):
    """
    Converts a PDF file into text using Azure Vision OCR, limiting the number of pages
    to process based on a central page (defined by 'page') and a number of pages before and after ('n').

    Args:
        pdf_path (str): Path to the PDF to convert.
        page (int, optional): Number of the central page to process. If None, the entire PDF is processed.
        n (int): The number of pages before and after 'page' to analyze.
        dpi (int): DPI (Dots Per Inch) to use when converting PDF pages to images.

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
        pages_to_process = convert_from_path(pdf_path)

    print(f"Pages to process: {len(pages_to_process)}")

    # Multiprocessing to handle multiple pages in parallel
    with multiprocessing.Pool() as pool:
        page_texts = pool.map(process_single_page_with_azure, pages_to_process)

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
    dpi = 200  # Use a sensible DPI

    # Call the function to convert the PDF to text
    start_time = time.time()
    text = pdf_to_text(pdf_path, page=target_page, n=n_range)
    print(text)
    print(len(text))
    end_time = time.time()

    print(f"Time elapsed: {end_time - start_time:.2f} seconds")