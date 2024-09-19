import os

from dotenv import load_dotenv
from pymongo import MongoClient

from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings

# Load the environment variables
load_dotenv(override=True)

def extract_context_from_vector_search(query: str = 'white', k: int = 4):

    MONGO_URI=os.environ["URI_MONGODB_VECTOR_SEARCH"]
    DB_NAME = "apec_db"
    COLLECTION_NAME_EMBEDDING = "apec_vectorstores"
    ATLAS_VECTOR_SEARCH_INDEX_NAME = "vector_index"

    # Load the environment variables
    load_dotenv(override=True)
    # Configure the MongoDB client
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME_EMBEDDING]

    # # Filter to extract only the documents in the filtered list
    # filter_spec = {"id": {"$in": ids_filtered_docs}}

    # Create the connection to MongoDB and VectorSearch
    vector_search = MongoDBAtlasVectorSearch.from_connection_string(
        MONGO_URI,
        DB_NAME + "." + COLLECTION_NAME_EMBEDDING,
        embedding=OpenAIEmbeddings(disallowed_special=(), model='text-embedding-3-large'),
        index_name = ATLAS_VECTOR_SEARCH_INDEX_NAME,
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
    return string


# Example usage
if __name__ == '__main__':
    results = extract_context_from_vector_search()
    print(results)  # Print the results of the vector search