from google.cloud import storage
import os
import io

BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "shaq-invitaciones-bucket")

def upload_bytes_to_gcs(image_bytes: bytes, destination_blob_name: str, content_type: str = "image/png") -> str:
    """
    Sube bytes a Google Cloud Storage y retorna la URL pública.
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_file(io.BytesIO(image_bytes), content_type=content_type)
        
        # Hacemos el archivo público para que sea accesible
        # Nota: El bucket debe permitir acceso público o ACLs
        # Si falla make_public por políticas de bucket, retornamos la URL autenticada o firmada
        try:
            blob.make_public()
        except Exception as e:
            print(f"Warning making blob public: {e}")
            # Si no se puede hacer público, igual retornamos la URL
            # O podríamos generar una signed URL aquí
            pass

        return blob.public_url

    except Exception as e:
        print(f"Error uploading to GCS: {e}")
        # Retorna None o lanza excepción según prefieras
        raise e

def list_files(prefix: str):
    """Lista todos los archivos en el bucket que coinciden con el prefijo."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs(prefix=prefix)
        return list(blobs)
    except Exception as e:
        print(f"Error listing files from GCS: {e}")
        return []

def delete_files(blob_names: list):
    """Elimina una lista de archivos del bucket."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        batch = storage_client.batch()
        
        # Eliminar en batch es más eficiente, pero la librería de python no tiene un batch explícito simple
        # para delete, así que iteramos. Ojo: batch() es un context manager.
        with batch:
            for name in blob_names:
                blob = bucket.blob(name)
                blob.delete()
                
    except Exception as e:
        print(f"Error deleting files from GCS: {e}")

