import os

from scripts.auxiliar_functions import absolute_path

from dotenv import load_dotenv
from pymongo import MongoClient

from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# Load the environment variables
load_dotenv(override=True)

def extract_context_from_vector_search(query: str = 'white', k: int = 4):

    # MONGO_URI=os.environ["URI_MONGODB_VECTOR_SEARCH"]
    # DB_NAME = "apec_db"
    # COLLECTION_NAME_EMBEDDING = "apec_vectorstores_official"
    # ATLAS_VECTOR_SEARCH_INDEX_NAME = "vector_index"

    # # Configure the MongoDB client
    # client = MongoClient(MONGO_URI)
    # db = client[DB_NAME]
    # collection = db[COLLECTION_NAME_EMBEDDING]

    # # Filter to extract only the documents in the filtered list
    # filter_spec = {"id": {"$in": ids_filtered_docs}}

    # # Create the connection to MongoDB and VectorSearch
    # vector_search = MongoDBAtlasVectorSearch.from_connection_string(
    #     MONGO_URI,
    #     DB_NAME + "." + COLLECTION_NAME_EMBEDDING,
    #     embedding=OpenAIEmbeddings(disallowed_special=(), model='text-embedding-3-large'),
    #     index_name = ATLAS_VECTOR_SEARCH_INDEX_NAME,
    # )

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

    # Convert the list to an unique
    filter_list = list(set(filter_list))
    
    string = " ".join(map(str, filter_list))

    # Now return sources info:
    sources = [dict.metadata['source'] for dict, _ in results]

    return string, sources


# Example usage
if __name__ == '__main__':
    string, sources = extract_context_from_vector_search()
    print(sources)  # Print the results of the vector search