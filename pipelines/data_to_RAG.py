# Python Imports
import os
import re

# Third party imports
from dotenv import load_dotenv
import pypandoc
from docx2pdf import convert as docx_to_pdf
import subprocess
import platform
import traceback
from uuid import uuid4
import pandas as pd

# Langchain imports
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
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
        
        # Define the vector store
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
        
    def filter_documents(self, documents: list):
        """
        Filters the documents based on the length and the number of words
        """
        filtered_documents = []

        def contains_only_numbers_and_symbols(text):
            """Verifica si el texto contiene solo números y símbolos (sin caracteres alfabéticos)."""
            return not any(char.isalpha() for char in text)

        for doc in documents:
            # Extract the page content
            page_content = doc.page_content

            if (contains_only_numbers_and_symbols(page_content) or 
                len(page_content) < 25):
                continue
            else:
                filtered_documents.append(doc)

        return filtered_documents

    def add_metadata(self, documents: list, type: str) -> list:
        """
        Adds metadata to the documents
        """
        for doc in documents:
            doc.metadata['type_data'] = type

        return documents
    
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

            # Filter the documents
            documents_pdf = self.filter_documents(documents_pdf)

            # Add metadata to the documents
            documents_pdf = self.add_metadata(documents_pdf, type='text')

            if not documents_pdf:
                return False
            
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
        

    def process_tabular(self, filepath: str):
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

            # Load the file with pandas
            df = pd.read_excel(filepath)

            # Build Documents with the information
            documents_xls = []
            for _, row in df.iterrows():
                # Filtrar columnas que no estén nombradas (evitar "Unnamed")
                valid_columns = [col for col in df.columns if not col.startswith('Unnamed')]
                
                # Comprobar que la fila tiene al menos un valor no nulo en las columnas válidas
                if not row[valid_columns].isnull().all():
                    # Crear un string para cada fila concatenando "Columna: Valor" para cada columna
                    page_content = "\n".join([f"{col}: {row[col]}" for col in valid_columns if pd.notnull(row[col])])

                    # Agregar el string de la fila a la lista resultado
                    documents_xls.append(Document(page_content=page_content, metadata={'source': filepath}))

            # Filter the documents
            documents_xls = self.filter_documents(documents_xls)

            # Add metadata to the documents
            documents_xls = self.add_metadata(documents_xls, type='tabular')

            if not documents_xls:
                return False
            
            # Save the processed data
            self.documents.extend(documents_xls)

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
        uuids = [str(uuid4()) for _ in range(len(self.documents))]

        self.vector_store.add_documents(documents=self.documents, ids=uuids)

        return 'Success'


# Define the base path to process the data
base_path = '../data/APEC_ChromaDB'

# Create an Object to process the data
process_data = ProcessData()
base_path = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), base_path))

# List of file extensions that can be converted to PDF
convertible_to_pdf = ['.docx', '.doc', '.txt', '.html', '.htm', '.xml', '.rtf', '.pptx', '.ppt']
tabular_files = ['.xlsx', '.xls']

# Function to convert files to PDF using Pandoc
def convert_to_pdf_pandoc(file_path, output_pdf_path):
    try:
        print(f"Trying to convert with Pandoc: {file_path}")
        # Try converting using pypandoc
        pypandoc.convert_file(file_path, 'pdf', outputfile=output_pdf_path)
        return True
    except Exception:
        print(f"Error converting {file_path} to PDF with Pandoc.")
        print(traceback.format_exc())  # Log the detailed error trace
        return False

# Function to convert files to PDF using LibreOffice if Pandoc fails
def convert_to_pdf_libreoffice(input_file, output_dir):
    try:
        print(f"Trying to convert with LibreOffice: {input_file}")
        # Run LibreOffice in terminal to convert the file to PDF
        subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', output_dir, input_file], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting {input_file} to PDF with LibreOffice: {e}")
        return False

# Function to log files that fail to convert to PDF
def log_failed_file(file_path):
    with open(process_data.error_files, 'a') as error_log:
        error_log.write(file_path + '\n')  # Add the failed file to the error log

# Iterate over all files in the directory
for dirpath, dirnames, filenames in os.walk(base_path):
    for filename in filenames:
        # Extract the file extension
        file_extension = os.path.splitext(filename)[1].lower()

        # If the file is already a PDF, process it as usual
        if file_extension == '.pdf':
            pdf_path = os.path.join(dirpath, filename)
            result = process_data.process_pdf(pdf_path)

            if result == 'Success':
                with open(process_data.history_file, 'r') as file:
                    number_files = len(file.read().splitlines())
                    print("Number of files processed: ", number_files)

        # Process tabular files            
        elif file_extension in tabular_files:
            xls_path = os.path.join(dirpath, filename)
            result = process_data.process_tabular(xls_path)

            if result == 'Success':
                with open(process_data.history_file, 'r') as file:
                    number_files = len(file.read().splitlines())
                    print("Number of files processed: ", number_files)

        # If the file can be converted to PDF
        elif file_extension in convertible_to_pdf:
            original_file_path = os.path.join(dirpath, filename)
            output_pdf_name = os.path.splitext(filename)[0] + '.pdf'
            output_pdf_path = os.path.join(dirpath, output_pdf_name)

            # Convert only if the PDF file doesn't already exist
            if not os.path.exists(output_pdf_path):
                # 1. Try with Pandoc
                conversion_success = convert_to_pdf_pandoc(original_file_path, output_pdf_path)

                # 2. If Pandoc fails, try with LibreOffice
                if not conversion_success:
                    print(f"Trying alternative conversion for {filename} with LibreOffice")
                    conversion_success = convert_to_pdf_libreoffice(original_file_path, dirpath)

                # If any conversion was successful, process the PDF
                if conversion_success:
                    result = process_data.process_pdf(output_pdf_path)

                    if result == 'Success':
                        with open(process_data.history_file, 'r') as file:
                            number_files = len(file.read().splitlines())
                            print("Number of files processed: ", number_files)
                    else:
                        print(f"File {output_pdf_path} processed but not marked as successful.")
                else:
                    # If all conversion attempts failed, log the file
                    print(f"All conversion methods failed for {original_file_path}. Logging error.")
                    log_failed_file(original_file_path)
            else:
                print(f"{output_pdf_name} already exists. Skipping conversion.")