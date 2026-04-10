from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import pandas as pd
import uuid
import io
from pydantic import BaseModel
from app.models.schemas import Guest, GuestStatus
from app.services.db import get_db
from app.services.qr import generate_qr
from app.services.cloud_storage import upload_bytes_to_gcs, list_files, delete_files
from fastapi.responses import StreamingResponse
from fastapi import BackgroundTasks
import zipfile

# from google.cloud import firestore
from datetime import datetime

router = APIRouter(prefix="/api/guests", tags=["Guests"])
collection_name = "guests"

@router.post("/upload", response_model=List[Guest])
async def upload_guests(file: UploadFile = File(...)):
    import os
    import base64
    import traceback
    import random

    try:
        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(status_code=400, detail="Invalid file format. Please upload CSV or Excel.")

        contents = await file.read()
        if file.filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding='latin1')
        else:
            df = pd.read_excel(io.BytesIO(contents))

        # Clean columns
        df.columns = df.columns.astype(str).str.lower().str.strip()
        if "name" not in df.columns:
            raise HTTPException(status_code=400, detail="Missing required column: name")

        os.makedirs("qrs", exist_ok=True)
        db = get_db()
        
        # 1. Get existing data to ensure unique random IDs and compute consecutive offset
        existing_ids = set()
        existing_count = 0
        docs = db.collection(collection_name).stream()
        for doc in docs:
            d = doc.to_dict()
            if "id" in d:
                existing_ids.add(str(d["id"]))
            existing_count += 1

        guests_added = []
        batch = db.batch()

        for idx, row in df.iterrows():
            guest_uuid = str(uuid.uuid4())
            
            # 2. Consecutive ID (continues from existing count)
            id_consecutivo = str(existing_count + idx + 1)
            
            # 3. Random unique 6-digit ID
            while True:
                new_id = str(random.randint(100000, 999999))
                if new_id not in existing_ids:
                    existing_ids.add(new_id)
                    current_id = new_id
                    break

            qr_code_base64 = generate_qr(guest_uuid)
            
            # Filename uses consecutive ID + name for easy sorting
            safe_name = "".join(x for x in str(row["name"]) if x.isalnum() or x in " _-").strip()
            filename = f"{id_consecutivo}_{safe_name}.png"
            file_path = os.path.join("qrs", filename)
            
            if "," in qr_code_base64:
                img_data = base64.b64decode(qr_code_base64.split(",")[1])
            else:
                img_data = base64.b64decode(qr_code_base64)
                
            with open(file_path, "wb") as f:
                f.write(img_data)

            # Upload to GCS
            gcs_url = None
            try:
                gcs_url = upload_bytes_to_gcs(img_data, f"qrs/{filename}")
                # Si se subió con éxito a la nube, borramos el local para no saturar el servidor
                if gcs_url and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error uploading to GCS: {e}")
                gcs_url = None

            guest_email = row["email"] if "email" in df.columns and pd.notna(row["email"]) else None
            final_qr_url = gcs_url if gcs_url else qr_code_base64

            guest_data = {
                "id": current_id,
                "id_consecutivo": id_consecutivo,
                "name": row["name"],
                "email": guest_email,
                "uuid": guest_uuid,
                "qr_code_url": final_qr_url,
                "status": GuestStatus.VALID.value,
                "created_at": datetime.now()
            }
            
            doc_ref = db.collection(collection_name).document(guest_uuid)
            batch.set(doc_ref, guest_data)
            guests_added.append(guest_data)

        batch.commit()
        return guests_added


    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Guest])
async def get_guests():
    db = get_db()
    guests_ref = db.collection(collection_name)
    docs = guests_ref.stream()
    guests = []
    for doc in docs:
        d = doc.to_dict()
        # Convert timestamp... simplified for now
        guests.append(d)
    return guests

@router.get("/list", response_model=List[Guest])
async def list_all_guests():
    db = get_db()
    guests_ref = db.collection(collection_name)
    docs = guests_ref.stream()
    guests = []
    for doc in docs:
        d = doc.to_dict()
        guests.append(d)
    return guests

@router.get("/last-group", response_model=List[Guest])
async def get_last_group_qrs():
    # Helper to return guests with QRs from the most recent upload
    db = get_db()
    guests_ref = db.collection(collection_name)
    docs = guests_ref.stream()
    guests = []
    for doc in docs:
        d = doc.to_dict()
        guests.append(d)
    return guests

@router.get("/download-qrs", response_class=StreamingResponse)
async def download_all_qrs(background_tasks: BackgroundTasks):
    try:
        # 1. Listar archivos del bucket (carpeta qrs/)
        blobs = list_files("qrs/")
        if not blobs:
            raise HTTPException(status_code=404, detail="No QR codes found to download")

        # 2. Crear ZIP en memoria
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for blob in blobs:
                # Descargar contenido del blob
                file_content = blob.download_as_bytes()
                # Para el ZIP de 'todos', el blob ya tiene el nombre idconsecutivo_nombre.png
                archive_name = blob.name.replace("qrs/", "")
                zip_file.writestr(archive_name, file_content)
        
        zip_buffer.seek(0)

        # 3. Borrado desactivado a petición del usuario
        # blob_names_to_delete = [blob.name for blob in blobs]
        # background_tasks.add_task(delete_files, blob_names_to_delete)

        # 4. Retornar el archivo
        return StreamingResponse(
            zip_buffer, 
            media_type="application/zip", 
            headers={"Content-Disposition": "attachment; filename=todos_los_qrs.zip"}
        )

    except Exception as e:
        print(f"Error generating zip: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class DownloadSelectionRequest(BaseModel):
    uuids: List[str]

@router.post("/download-selected", response_class=StreamingResponse)
async def download_selected_qrs(body: DownloadSelectionRequest):
    """Recibe una lista de UUIDs y retorna un ZIP con sus QRs."""
    import base64

    if not body.uuids:
        raise HTTPException(status_code=400, detail="No se proporcionaron UUIDs.")

    try:
        db = get_db()
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for guest_uuid in body.uuids:
                doc = db.collection(collection_name).document(guest_uuid).get()
                if not doc.exists:
                    continue

                guest = doc.to_dict()
                name = "".join(x for x in str(guest.get("name", "guest")) if x.isalnum() or x in " _-").strip()
                
                # USAR EL ID CONSECUTIVO PARA EL NOMBRE DEL ARCHIVO EN EL ZIP
                guest_id = guest.get("id_consecutivo", guest.get("id", guest_uuid[:6]))
                
                filename = f"{guest_id}_{name}.png"
                qr_url = guest.get("qr_code_url", "")

                img_data = None

                if qr_url.startswith("data:"):
                    # Base64 embedded image
                    try:
                        header, encoded = qr_url.split(",", 1)
                        img_data = base64.b64decode(encoded)
                    except Exception as e:
                        print(f"Error decoding base64 for {guest_uuid}: {e}")
                elif qr_url.startswith("http"):
                    # GCS URL — download server-side (no CORS issue)
                    try:
                        from app.services.cloud_storage import list_files
                        import urllib.request
                        with urllib.request.urlopen(qr_url, timeout=10) as response:
                            img_data = response.read()
                    except Exception as e:
                        print(f"Error downloading GCS QR for {guest_uuid}: {e}")

                if img_data:
                    zip_file.writestr(filename, img_data)

        zip_buffer.seek(0)

        if zip_buffer.getbuffer().nbytes == 0:
            raise HTTPException(status_code=404, detail="No se encontraron imágenes para los UUIDs dados.")

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=qrs_seleccionados.zip"}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating selected zip: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.delete("/delete-all", response_model=dict)
async def delete_all_guests():
    """Borra todos los documentos de la colección 'guests' en Firestore."""
    try:
        db = get_db()
        guests_ref = db.collection(collection_name)
        docs = guests_ref.stream()
        
        deleted_count = 0
        batch = db.batch()
        
        for doc in docs:
            batch.delete(doc.reference)
            deleted_count += 1
            # Firestore batch limit is 500
            if deleted_count % 500 == 0:
                batch.commit()
                batch = db.batch()
        
        batch.commit()
        return {"status": "success", "message": f"Se borraron {deleted_count} invitados de Firestore."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-qrs-bucket", response_model=dict)
async def delete_all_qrs_bucket():
    """Borra todos los archivos de la carpeta 'qrs/' en Google Cloud Storage."""
    try:
        blobs = list_files("qrs/")
        if not blobs:
            return {"status": "info", "message": "No hay archivos en la carpeta qrs/."}
        
        blob_names = [blob.name for blob in blobs]
        delete_files(blob_names)
        
        return {"status": "success", "message": f"Se borraron {len(blob_names)} archivos del bucket GCS."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all", response_model=List[Guest])
async def get_all_guests_from_db():
    try:
        db = get_db()
        guests_ref = db.collection(collection_name)
        docs = guests_ref.stream()
        guests = []
        for doc in docs:
            d = doc.to_dict()
            guests.append(d)
        return guests
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GuestUpdateRequest(BaseModel):
    name: str

@router.put("/{uuid}/name", response_model=dict)
async def update_guest_name(uuid: str, body: GuestUpdateRequest):
    try:
        db = get_db()
        doc_ref = db.collection(collection_name).document(uuid)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Guest not found")
        
        doc_ref.update({"name": body.name})
        return {"status": "success", "message": "Name updated successfully"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class GuestStatusUpdate(BaseModel):
    status: str

@router.put("/{uuid}/status", response_model=dict)
async def update_guest_status(uuid: str, body: GuestStatusUpdate):
    from google.cloud import firestore
    try:
        db = get_db()
        doc_ref = db.collection(collection_name).document(uuid)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Guest not found")
        
        updates = {"status": body.status}
        if body.status == "valid":
            updates["scan_timestamp"] = firestore.DELETE_FIELD
        elif body.status == "checked_in":
            d = doc.to_dict()
            if "scan_timestamp" not in d:
                updates["scan_timestamp"] = datetime.now()
                
        doc_ref.update(updates)
        return {"status": "success", "message": "Status updated successfully"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
