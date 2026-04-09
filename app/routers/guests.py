from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import pandas as pd
import uuid
import io
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

        # Clean the columns to be lowercase and strip spaces
        df.columns = df.columns.astype(str).str.lower().str.strip()
        
        # We require at least "name"
        if "name" not in df.columns:
            raise HTTPException(status_code=400, detail=f"Missing required column: name")

        # Ensure qrs directory exists
        os.makedirs("qrs", exist_ok=True)
        
        db = get_db()
        
        # Get current count of guests from DB
        guests_ref = db.collection(collection_name)
        # Using aggregation query for count is more efficient but requires newer SDK/backend
        # For simplicity and broad compatibility:
        existing_docs = guests_ref.stream()
        existing_qrs = sum(1 for _ in existing_docs)
        start_index = existing_qrs + 1

        guests_added = []
        # db = get_db() # Moved up
        batch = db.batch()

        for idx, row in df.iterrows():
            guest_uuid = str(uuid.uuid4())
            qr_code_base64 = generate_qr(guest_uuid)
            
            # Save QR to file
            current_id = start_index + idx
            safe_name = "".join(x for x in str(row["name"]) if x.isalnum() or x in " _-").strip()
            filename = f"{current_id}_{safe_name}.png"
            file_path = os.path.join("qrs", filename)
            
            # Remove header "data:image/png;base64,"
            if "," in qr_code_base64:
                img_data = base64.b64decode(qr_code_base64.split(",")[1])
            else:
                img_data = base64.b64decode(qr_code_base64)
                
            with open(file_path, "wb") as f:
                f.write(img_data)

            # Upload to Google Cloud Storage
            gcs_url = None
            gcs_filename = f"qrs/{filename}"
            try:
                gcs_url = upload_bytes_to_gcs(img_data, gcs_filename)
            except Exception as e:
                print(f"GCS Upload failed: {e}")
                # Fallback: keep using base64 if upload fails
                gcs_url = None

            # Safely get email or set to None
            guest_email = row["email"] if "email" in df.columns and pd.notna(row["email"]) else None
            
            # Use GCS URL if available, else Base64
            final_qr_url = gcs_url if gcs_url else qr_code_base64

            guest_data = {
                "id": str(current_id),
                "name": row["name"],
                "email": guest_email,
                "uuid": guest_uuid,
                "qr_code_url": final_qr_url,
                "status": GuestStatus.VALID.value,
                "created_at": datetime.now()
            }
            
            doc_ref = db.collection(collection_name).document(guest_uuid)
            batch.set(doc_ref, guest_data)
            
            # We return the object with current time for response model
            guest_resp = guest_data.copy()
            guests_added.append(guest_resp)

        batch.commit()
        return guests_added

    except Exception as e:
        print("ERROR IN UPLOAD_GUESTS:")
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
                # Nombre del archivo dentro del zip (quitamos la carpeta para que estén en raíz del zip)
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
