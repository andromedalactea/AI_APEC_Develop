import os
from azure.storage.blob import BlobServiceClient, ContainerClient
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv(override=True)

# Parámetros de conexión (Usa SAS Token que configuraste antes)
blob_service_url = os.getenv("AZURE_BLOB_SERVICE_URL")
sas_token = f"?{os.getenv('AZURE_BLOB_SAS_TOKEN')}"

# Inicializa el cliente de Blob Storage usando URL + SAS Token
blob_service_client = BlobServiceClient(account_url=blob_service_url, credential=sas_token)

# Nombre del contenedor (previamente creado)
container_name = "johnny5container"
container_client = blob_service_client.get_container_client(container_name)

# Ruta de la carpeta local (usa rutas absolutas o relativas sin "normpath")
# Como estás en Linux, no necesitamos manipular las barras "/", simplemente definimos la ruta
# Function to generate the absolute path
def absolute_path(relative_path):
    return os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), relative_path))

# Ruta de la carpeta local
local_folder_path = absolute_path("../data/Test/COMMANDER SHELL")


# Definir el nombre de la carpeta madre que aparecerá en Azure Blob Storage
carpeta_madre_blob = "johnny5_data"  # Cambia esto por cualquier nombre que prefieras

# Extensiones permitidas para subir (ajusta según las que quieras permitir)
allowed_extensions = [".pdf", ".txt", ".png", ".xlsx", "xls", ".csv", ".jpg", ".jpeg", ".docx", ".doc"]

# Función para subir archivos
def upload_files_with_allowed_extensions():
    for root, dirs, files in os.walk(local_folder_path):
        for file in files:
            # Ignorar los archivos que no tengan las extensiones permitidas
            if any(file.lower().endswith(ext) for ext in allowed_extensions):
                # Construir la ruta relativa dentro del Blob respetando la estructura de carpetas
                relative_path = os.path.relpath(os.path.join(root, file), local_folder_path)

                # Concatenar la carpeta madre + relative_path para crear la ruta en el blob
                # Esto asegura que siempre exista un nombre para la raíz
                file_path_on_blob = os.path.join(carpeta_madre_blob, relative_path).replace("\\", "/")
                file_path_on_local = os.path.join(root, file)

                # Crear un cliente de blob para cada archivo
                blob_client = container_client.get_blob_client(file_path_on_blob)

                print(f"Subiendo archivo: {file_path_on_local} al Blob con ruta: {file_path_on_blob}")
                
                # Subir el archivo al contenedor en Azure Blob Storage
                with open(file_path_on_local, "rb") as data:
                    blob_client.upload_blob(data, overwrite=True)

                print(f"Archivo '{file}' subido exitosamente al contenedor en ruta: {file_path_on_blob}")
            else:
                print(f"Se omitió el archivo '{file}' ya que no tiene una extensión permitida.")

# Llamada a la función para comenzar la subida
upload_files_with_allowed_extensions()

print("Proceso de subida completado.")