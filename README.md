🚀 QR-Access Event Manager | Shaq O'Neal Private EventSistema de control de acceso en tiempo real mediante códigos QR, diseñado para alta velocidad y escalabilidad serverless. 🛠 Stack TecnológicoBackend: Python 3.13 + FastAPI (REST API). Frontend: HTML5, CSS3 (Vanilla JS) + Chart.js (Dashboard). Base de Datos: Google Firestore (NoSQL). Infraestructura: Google Cloud Run (Dockerized). Auth: JWT (JSON Web Tokens). 🏗 Estructura del ProyectoPlaintextqr-access-event/
├── app/
│ ├── main.py # Punto de entrada FastAPI [cite: 70]
│ ├── routers/ # Endpoints (guests, scanner, dashboard, auth) [cite: 70]
│ ├── services/ # Lógica de Firestore y Generación QR [cite: 71]
│ ├── models/ # Schemas de Pydantic [cite: 71]
│ └── static/ # UI (Dashboard, Scanner, Estilos) [cite: 71]
├── tests/ # Pruebas unitarias [cite: 72]
├── Dockerfile # Configuración de contenedor [cite: 72]
└── requirements.txt # Dependencias [cite: 72]
📋 Requerimientos Core1. Gestión de Invitados (RF-01 a RF-05)Carga: Importación masiva vía CSV/Excel. Generación: Crear QR único con UUID (sin datos personales visibles). Salida: Descarga individual o en paquete ZIP. 2. Validación y Escaneo (RF-06 a RF-11)Interfaz: Acceso por cámara desde navegador móvil. +1Reglas de Negocio:Válido: Pantalla Verde + "Bienvenido [Nombre]". +1Invalido: Pantalla Roja + "No registrado". +1Doble Entrada: Pantalla Naranja + "Ya utilizado" (con timestamp). +1Performance: Validación en < 2 segundos. 3. Dashboard Administrativo (RF-12 a RF-17)Métricas en tiempo real: Total invitados, ingresados y % de asistencia. Gráfica de flujo de ingresos (intervalos de 15/30 min). Historial de los últimos 50 ingresos. 🎨 Especificaciones de Diseño (Shaq Style)Primario: Dorado (#B8860B) para acentos y botones. Fondo: Negro Profundo (#0A0A0A). UX: Operación con una sola mano para el personal de seguridad. 🛠 Configuración de Desarrollo1. Variables de Entorno (.env.local)Code snippetFIRESTORE_EMULATOR_HOST=localhost:8080
GOOGLE_CLOUD_PROJECT=shaq-event-qr
JWT_SECRET=tu_secreto_aleatorio
USERNAME_ADMIN=admin
PASSWORD_ADMIN=admin123 2. Comandos de EjecuciónIniciar Emulador Firestore: firebase emulators:start --only firestore Instalar Dependencias: pip install -r requirements.txt Correr App: uvicorn app.main:app --reload 🔗 Endpoints ClaveMétodoEndpointDescripciónPOST/api/auth/loginObtención de token JWT. POST/api/guests/uploadCarga masiva y generación de QRs. POST/api/scanner/validateValidación de UUID y registro de acceso. GET/api/dashboard/statsEstadísticas generales para el Admin.
