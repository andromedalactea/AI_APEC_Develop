import os

from scripts.auxiliar_functions import absolute_path

from dotenv import load_dotenv
from pymongo import MongoClient

from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# Load the environment variables
load_dotenv(override=True)

def extract_context_from_vector_search(query: str = '', k: int = 4):

    # Data directory absolute path
    data_directory = absolute_path("../data/APEC_ChromaDB")

    vector_search= Chroma(
                    collection_name="apec_vectorstores",
                    embedding_function=OpenAIEmbeddings(disallowed_special=(), model='text-embedding-3-large'),
                    persist_directory=data_directory,  
                )
    # Perform the similarity search with a filter
    results = vector_search.similarity_search_with_score(
        query = query ,
        k = k,  # Limit to the number of IDs provided
    )

    filter_list = [dict.page_content for dict, _ in results]

    # Add the number of sources in string format
    for index, item in enumerate(filter_list):
        filter_list[index] = f"\nSOURCE #{index+1}:\n {item}"

    # Convert the list to an unique
    filter_list = list(set(filter_list))
    print(filter_list)
    string = " ".join(map(str, filter_list))

    # Now return sources info:
    sources = [(data.metadata['source'], data.metadata['page']) for data, _ in results]

    return string, sources


# Example usage
if __name__ == '__main__':
    string, sources = extract_context_from_vector_search('Saturn', 4)
    print(string, sources)  # Print the results of the vector search