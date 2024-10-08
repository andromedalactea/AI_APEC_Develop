import os

from scripts.auxiliar_functions import absolute_path
from scripts.tesserac import pdf_to_text

from dotenv import load_dotenv
from pymongo import MongoClient

from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# Load the environment variables
load_dotenv(override=True)

def extract_context_from_vector_search(query: str = '', k: int = 4):

    # Data directory absolute path
    data_directory = absolute_path(os.getenv('PATH_VECTOR_DB'))

    vector_search= Chroma(
                    collection_name="apec_vectorstores",
                    embedding_function=OpenAIEmbeddings(disallowed_special=(), model='text-embedding-3-small'),
                    persist_directory=data_directory,  
                )
    # Perform the similarity search with a filter
    results = vector_search.similarity_search_with_score(
        query = query ,
        k = k,  # Limit to the number of IDs provided
    )

    filter_list = [dict.page_content for dict, _ in results]

    filter_list = []
    for index, (doc, score) in enumerate(results):  # Ajuste aquí: desestructurar correctamente
        # Verificamos si el documento tiene el campo 'page' en la metadata
        if 'page' in doc.metadata:
            # Si tiene el campo 'page', usamos OCR para extraer el texto de la página correspondiente
            pdf_path = doc.metadata['source']
            page_number = doc.metadata['page']
            try:
                extracted_text = pdf_to_text(pdf_path, page=page_number + 1, n=1)

                # Se guarda el texto extraído de la página en lugar del contenido normal
                processed_text = f"\nSOURCE #{index+1}:\n {extracted_text}"
            except Exception as e:
                print(f"Error in extracting text from PDF: {e}")
                # Si hay un error, se usa el page_content como está
                processed_text = f"\nSOURCE #{index+1}:\n {doc.page_content}"

        else:
            # Si no tiene el campo 'page', usamos el page_content como está
            processed_text = f"\nSOURCE #{index+1}:\n {doc.page_content}"

        filter_list.append(processed_text)

    # Convert the list to an unique
    filter_list = list(set(filter_list))
    string = " ".join(map(str, filter_list))

    # Now return sources info:
    sources = [(data.metadata.get('source', 'Unknown Source'), data.metadata.get('page')) for data, _ in results]


    return string, sources


# Example usage
if __name__ == '__main__':
    string, sources = extract_context_from_vector_search('TLS Console require maintenance?', 2)
    print(string, sources)  # Print the results of the vector search