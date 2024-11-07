import os
from azure.storage.blob import ContainerClient

# Parámetros de conexión (SAS Token)
blob_service_url = os.getenv("AZURE_BLOB_SERVICE_URL")
sas_token = f"?{os.getenv('AZURE_BLOB_SAS_TOKEN')}"

# Nombre del contenedor
container_name = "johnny5-container"

# Inicializa el cliente del contenedor
container_client = ContainerClient(account_url=blob_service_url, credential=sas_token, container_name=container_name)

# Función para eliminar todos los blobs del contenedor
def delete_all_blobs():
    blobs = container_client.list_blobs()
    blob_count = 0

    for blob in blobs:
        print(f"Eliminando blob: {blob.name}")
        # Elimina el blob
        container_client.delete_blob(blob)
        blob_count += 1

    if blob_count == 0:
        print(f"El contenedor '{container_name}' ya está vacío.")
    else:
        print(f"Se han eliminado {blob_count} blobs del contenedor '{container_name}'.")

# Llamada a la función para eliminar todos los blobs
delete_all_blobs()

print("Proceso de eliminación completado.")