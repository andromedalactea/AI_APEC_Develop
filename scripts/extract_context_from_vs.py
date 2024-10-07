import os
import time
from scripts.auxiliar_functions import absolute_path
from scripts.tesserac import pdf_to_text  # Assuming this is your modified pdf_to_text function

from dotenv import load_dotenv
from pymongo import MongoClient

from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# Import required for multiprocessing
from multiprocessing import Pool

# Load the environment variables
load_dotenv(override=True)

def process_single_result(args):
    """
    Process a single result from the vector search.

    Args:
        args (tuple): Tuple containing index, doc, and score.

    Returns:
        str: The processed text for this result.
    """
    index, doc, score = args

    # Check if the document has a 'page' field in metadata
    if 'page' in doc.metadata:
        pdf_path = doc.metadata['source']
        page_number = doc.metadata['page']
        try:
            # Extract text from the specific page using pdf_to_text
            # Set num_workers=1 to avoid too many nested processes
            extracted_text = pdf_to_text(pdf_path, page=page_number + 1, n=1, num_workers=1)

            # Use the extracted text as the processed text
            processed_text = f"\nSOURCE #{index + 1}:\n {extracted_text}"
        except Exception as e:
            print(f"Error in extracting text from PDF: {e}")
            # If there's an error, use the page_content as is
            processed_text = f"\nSOURCE #{index + 1}:\n {doc.page_content}"
    else:
        # If there's no 'page' field, use the page_content as is
        processed_text = f"\nSOURCE #{index + 1}:\n {doc.page_content}"
    print(processed_text)
    return processed_text

def extract_context_from_vector_search(query: str = '', k: int = 4):
    """
    Perform a vector search and extract context from the results using pdf_to_text in parallel.

    Args:
        query (str): The query string for the vector search.
        k (int): The number of top results to consider.

    Returns:
        tuple: A string containing the extracted text and a list of source information.
    """

    # Data directory absolute path
    data_directory = absolute_path(os.getenv('PATH_VECTOR_DB'))

    vector_search = Chroma(
        collection_name="apec_vectorstores",
        embedding_function=OpenAIEmbeddings(disallowed_special=(), model='text-embedding-3-small'),
        persist_directory=data_directory,
    )
    # Perform the similarity search with a filter
    results = vector_search.similarity_search_with_score(
        query=query,
        k=k,  # Limit to the number of IDs provided
    )

    # Prepare arguments for parallel processing
    args_list = [(index, doc, score) for index, (doc, score) in enumerate(results)]

    # Use multiprocessing Pool to process results in parallel
    # Adjust the number of processes if needed
    with Pool(processes=min(k, os.cpu_count())) as pool:
        filter_list = pool.map(process_single_result, args_list)

    # Remove duplicates
    filter_list = list(set(filter_list))
    # Combine the texts into a single string
    string = " ".join(map(str, filter_list))

    # Now return sources info:
    sources = [(data.metadata.get('source', 'Unknown Source'), data.metadata.get('page')) for data, _ in results]

    return string, sources

# Example usage
if __name__ == '__main__':
    start_time = time.time()
    string, sources = extract_context_from_vector_search('TLS Console require maintenance?', 2)
    print(string)
    print(sources)  # Print the results of the vector search
    end_time = time.time()
    print(f"Time elapsed: {end_time - start_time:.2f} seconds")