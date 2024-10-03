# Python Imports
import os
import re
import gc

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
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Load the environment variables
load_dotenv(override=True)

def absolute_path(relative_path):
    return os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), relative_path))

class ProcessData:
    def __init__(self,
                 data_directory: str =  "../data/APEC_ChromaDB_v2",
                 history_file: str = "../data/processed_files_v2.txt",
                 error_file: str = "../data/error_files_v2.txt",
                 embedding_model: str = "text-embedding-3-small"):
        
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
        self.text_splitter = RecursiveCharacterTextSplitter(
                                                            # Set a really small chunk size, just to show.
                                                            chunk_size=1200,
                                                            chunk_overlap=400,
                                                            length_function=len,
                                                            is_separator_regex=False,
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
        
    def remove_repeated_phrases(self, text, n_words=8):
        """
        Esta función divide el texto en bloques de n palabras y elimina 
        aquellos bloques que se repiten consecutivamente, ya estén pegados o no.
        
        :param text: Texto procesado hasta este punto.
        :param n_words: Definir el tamaño de bloques de palabras a comparar (por ejemplo, 8 palabras por bloque).
        :return: Texto con bloques repetidos eliminados.
        """
        # Dividir en palabras
        words = text.split()

        # Procesar por bloques de n palabras consecutivas
        result = []
        i = 0
        while i < len(words):
            # Tomamos un bloque de n palabras
            block = ' '.join(words[i:i + n_words])
            
            # Solo añadimos el bloque si no es igual al último añadido
            if not result or block != result[-1]:
                result.append(block)

            i += n_words  # Movernos al siguiente bloque
            
        # Unir bloques de nuevo en una cadena
        return ' '.join(result)    

    def preprocess_page_content(self, text):
        """
        Performs preprocessing on the text to remove irrelevant characters/services and normalize the text.
        It removes strange or repetitive characters and normalizes excess whitespace.
        """
        # Convert to lowercase
        processed_text = text.lower()

        # Step 1: Remove sequences starting with "/" and with "\"
        processed_text = re.sub(r'/\S+', ' ', processed_text)  # Remove sequences like "/..."
        processed_text = re.sub(r'\\\S+', ' ', processed_text)  # Remove sequences like "\..."

        # Step 2: Remove placeholders with underscores like "fp__&__"
        processed_text = re.sub(r'\b\w+__&__\b', ' ', processed_text)

        # Step 3: Remove lines with more than three consecutive hyphens (---)
        processed_text = re.sub(r'-{3,}', ' ', processed_text)

        # Step 4: Remove non-ASCII characters (only retain printable ASCII)
        processed_text = re.sub(r'[^\x20-\x7E]', ' ', processed_text)

        # Step 5: Remove emojis and other rare alphanumeric characters
        # We use a regular expression to remove emojis (common Unicode emoji ranges) and other unusual characters.
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # Emoticons
            u"\U0001F300-\U0001F5FF"  # Symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # Transport and map symbols
            u"\U0001F1E0-\U0001F1FF"  # Flags (iOS)
            u"\u2600-\u26FF"          # Miscellaneous symbols
            u"\u2700-\u27BF"          # Dingbats
            "]+", flags=re.UNICODE)
        processed_text = emoji_pattern.sub(r' ', processed_text)  # Remove emojis

        # processed_text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", " ", processed_text)  # Optionally remove IP addresses
        processed_text = re.sub(r"\d{2,}\b", " ", processed_text)  # Remove larger numbers likely not semantically important

        # Remove excessive punctuation (replace sequences of dots, commas, etc. with a single space)
        processed_text = re.sub(r"[.,:;!]+", " ", processed_text)

        # Remove standalone numbers that add little semantic value
        processed_text = re.sub(r'\b\d+\b', ' ', processed_text)

        # Step 6: Remove generic placeholders and example values (e.g., xx, xxx, YYYY, mm-dd, etc.)
        processed_text = re.sub(r'\b(?:xx|xxx|xxxx|mm-dd(?:-yy)?|yyyy)\b', ' ', processed_text)

        # Step 7: Remove excessive whitespace (reduce multiple spaces to a single space)
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()

        # Step 8: Remove consecutive repeated words
        words = processed_text.split()
        processed_text = ' '.join([words[i] for i in range(len(words)) if i == 0 or words[i] != words[i-1]])

        # Step 9: Process repetitive phrases and remove them
        processed_text = self.remove_repeated_phrases(processed_text)

        return processed_text


    def filter_documents(self, documents: list):
        """
        Filters the documents based on the length and cleans the content to remove irrelevant characters.
        """

        filtered_documents = []

        def contains_only_numbers_and_symbols(text):
            """Verifica si el texto contiene solo números y símbolos (sin caracteres alfabéticos)."""
            return not any(char.isalpha() for char in text)

        for doc in documents:
            # Preprocess the page content before doing any checks
            page_content = self.preprocess_page_content(doc.page_content)

            if len(page_content) < 25:
                # Skip fragments that are too short
                continue
            elif contains_only_numbers_and_symbols(page_content):
                # Skip fragments that are just symbols and numbers
                continue

            # Update the document with the newly preprocessed page content
            doc.page_content = page_content

            # Append filtered and preprocessed document
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
            print(documents_pdf)
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

            # Clean the memory
            del loader, data
            gc.collect()

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

            # Clean the memory
            del df
            gc.collect()
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
base_path = '../data/pdf'

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