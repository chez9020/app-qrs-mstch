import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()

# Inicialización de Firebase / Google Cloud Firestore
if not firebase_admin._apps:
    try:
        # Intenta usar credenciales por defecto (Cloud Run usa esto automáticamente)
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {
            'projectId': os.getenv('GOOGLE_CLOUD_PROJECT', 'shaq-brand-bot'),
        })
    except Exception as e:
        print(f"Warning: Could not load default credentials: {e}")
        # En Cloud Run, a veces initialize_app() sin argumentos agarra la identidad del servicio
        try:
             firebase_admin.initialize_app()
        except ValueError:
            pass # Ya inicializado

db = firestore.client()

def get_db():
    return db
