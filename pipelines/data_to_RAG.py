# Python Imports
import os
import re

# Third party imports
from dotenv import load_dotenv


# Langchain imports
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_mongodb.vectorstores import MongoDBAtlasVectorSearch
from pymongo import MongoClient

# Load the environment variables
load_dotenv(override=True)

def absolute_path(relative_path):
    return os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), relative_path))

class ProcessData:
    def __init__(self,
                 data_directory: str =  "../data/APEC_ChromaDB",
                 history_file: str = "../data/processed_files.txt",
                 error_file: str = "../data/error_files.txt",
                 embedding_model: str = "text-embedding-3-large"):
        
        # List to store the documents temporarily
        self.documents = []

        # History file
        self.history_file = absolute_path(history_file)
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

        # Error file
        self.error_file = absolute_path(error_file)
        os.makedirs(os.path.dirname(self.error_file), exist_ok=True)
        

        # Define the Database to store the embeddings
        self.data_directory = absolute_path(data_directory)

        # Load already processed files into memory
        self.processed_files = self.load_processed_files()

        # Define the initial text splitter
        self.text_splitter = CharacterTextSplitter(
            separator="\n",  # Use line breaks as separator
            chunk_size=2000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False
        )

        # Embedding Model
        self.embedding_openai = OpenAIEmbeddings(model=embedding_model)

        # Verify the data directory
        os.makedirs(self.data_directory, exist_ok=True)  # Create the directory and any necessary parent directories
        # os.chmod(self.data_directory, 0o777) 
        ## Vector Store Chroma
        # Initialize MongoDB python client
        client = MongoClient(os.getenv("URI_MONGODB_VECTOR_SEARCH"))

        DB_NAME = "apec_db"
        COLLECTION_NAME = "apec_vectorstores"
        ATLAS_VECTOR_SEARCH_INDEX_NAME = "vector_index"

        MONGODB_COLLECTION = client[DB_NAME][COLLECTION_NAME]

        # self.vector_store = MongoDBAtlasVectorSearch(
        #     collection=MONGODB_COLLECTION,
        #     embedding=self.embedding_openai,
        #     index_name=ATLAS_VECTOR_SEARCH_INDEX_NAME,
        #     relevance_score_fn="cosine",
        # )
        self.vector_store = Chroma(
                    collection_name="apec_vectorstores",
                    embedding_function=self.embedding_openai,
                    persist_directory=self.data_directory,  
                )

    def load_processed_files(self):
        """
        Loads the processed files from the history file into a list
        """
        try:
            with open(self.history_file, 'r') as file:
                return set(file.read().splitlines())
        except FileNotFoundError:
            return set()

    def process_pdf(self, filepath: str):
        """
        This Method processes a PDF file and puts the documents into the self.documents list
        :param filepath: The path to the PDF file
        :return: 'Success' if the file was processed, 'Skipped' if it was already processed
        """

        try:
            # Verify if the file was already processed
            if filepath in self.processed_files:
                print(f"{filepath} already processed. Skipping.")
                return 'Skipped'

            # Load the file
            loader = PyPDFLoader(filepath)
            data = loader.load()

            # Split the text into chunks
            documents_pdf = self.text_splitter.split_documents(data)
            print("Number of documents:", len(documents_pdf))

            # Save the processed data
            self.documents.extend(documents_pdf)

            # If there are many documents, save and free the memory
            if len(self.documents) > 50:
                status_save = self.save_procceced_data_into_vector_store()
                if status_save == 'Success':
                    self.documents = []  # Clear documents to free memory
                    print("Data was processed and saved")

            # Save the file in the history after processing
            self.processed_files.add(filepath)  # Add to in-memory history
            with open(self.history_file, 'a') as file:
                file.write(filepath + "\n")

            return 'Success'
        except Exception as e:
            print(f"Error processing file {filepath}: {e}")
            with open(self.error_file, 'a') as file:
                file.write(filepath + str(e) + "\n")
            return 'Error'

    def save_procceced_data_into_vector_store(self):
        """
        Saves the processed data into a vector store
        :param documents_to_save: List of processed documents
        :return: 'Success' if saved successfully
        """
        # Save the data in the vector store
        self.vector_store.add_documents(documents=self.documents)

        return 'Success'


# Define the base path to process the data
base_path = '/mnt/apec-ai-feed/'

# Create an Object to process the data
process_data = ProcessData()
base_path = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), base_path))

# Iterate over all files in a directory
for dirpath, dirnames, filenames in os.walk(base_path):

    # Explore the files
    for filename in filenames:
        
        # Extract the extension
        file_extension = os.path.splitext(filename)[1].lower()

        if file_extension == '.pdf':
            
            # Process the PDF file
            result = process_data.process_pdf(os.path.join(dirpath, filename))
            
            # If the file was processed successfully
            if result == 'Success':
                # How many files were processed
                with open(process_data.history_file, 'r') as file:
                    number_files = len(file.read().splitlines())
                    print("Number of files processed: ", number_files)
