# 📌 AttendCare

Sistema de gestión de asistencias para servidores de iglesia, con registro en kiosko, control de eventos y reconciliación de participación.

---

# 🚀 1. Descripción General

AttendCare permite:

* Registrar eventos (cultos, oración, clases, etc.)
* Registrar asistencia mediante kiosko (huella/PIN)
* Controlar participación real:

  * Asistió
  * Reemplazó
  * Voluntario
  * Ausente
* Gestionar ministerios y servidores

---

# 🧱 2. Arquitectura

* Backend: Django + Django REST Framework
* Frontend: Vue.js (Vite)
* Base de datos: PostgreSQL
* Contenedores: Docker

---

# ⚙️ 3. Requisitos

* Docker
* Docker Compose
* Git

---

# 📦 4. Instalación

## 🔽 Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd attendCare
```

---

## 🔐 Variables de entorno

Crear archivo `.env`:

```env
DB_NAME=attendcare
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
```

---

## 🐳 Ejecutar el sistema

```bash
docker compose up --build
```

---

## 🌐 Accesos

* Backend: http://localhost:8000
* Frontend (templates): http://localhost:8000
* DB: localhost:5432

---

# 🧠 5. Convenciones de Desarrollo (IMPORTANTE)

## 🐍 Backend (Django)

### 📌 Herramientas obligatorias

* Black → formatea automáticamente el código
* Flake8 → detecta errores y malas prácticas

---

### 📌 Reglas de código

#### Nombres

* Variables:

  ```python
  nombreServidor
  fechaEvento
  ```

* Clases:

  ```python
  class Servidor:
  class Evento:
  ```

* Funciones:

  ```python
  def registrarAsistencia():
  ```

---

### 📌 Estructura por módulo

Cada módulo debe tener:

```bash
app/asistencias/
│
├── models.py
├── serializers.py
├── views.py
├── urls.py
```

---

### 📌 Responsabilidad de cada capa

* models → estructura BD
* serializers → JSON ↔ objeto
* views → lógica de negocio
* urls → rutas API

---

## 🌐 Frontend (Vue)

### 📌 Herramientas obligatorias

* ESLint → detecta errores
* Prettier → formatea código

---

# 🌿 6. Git Flow (OBLIGATORIO)

### Ramas

* main → producción
* develop → desarrollo
* feature-"Iniciales Quien Crea La Rama"/* → nuevas funcionalidades. Ej: infraestructura-II

---

### Flujo de trabajo

```bash
git checkout develop
git pull

git checkout -b infraestructura-II

# trabajar...

git add .
git commit -m "feat: Se crea infraestructura de proyecto"

git push origin infraestructura-II
```

---

# 🧪 7. Linter y Formatter

## Backend

```bash
black .
flake8 .
```

---

## Frontend

```bash
npm run lint
```

---

# 🗄️ 8. Base de Datos

* Motor: PostgreSQL
* Dentro de Docker: `db:5432`
* Desde tu PC: `localhost:5432`

---

# 📁 11. Estructura del Proyecto

```bash
attendCare/
│
├── app/                  # Django
├── docker/
│   ├── backend/
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── .env
└── README.md
```

---

# 🧠 12. Buenas Prácticas

❌ No subir:

* .env
* venv/
* env/
* _pycache__/
* *.pyc
* .DS_Store
* *.log

---

✔ Commits claros:

* feat: crear endpoint de asistencia
* fix: error conexión DB

---

✔ No subir a staging sin autorización o main sin revisión previa

---

## 🧱 Migraciones

Ejecutar dentro del contenedor:

```bash
docker exec -it church_backend python manage.py migrate
```

---

## 🔐 Autenticación

El sistema utiliza JWT:

- Login: `/api/auth/login/`
- Refresh: `/api/auth/refresh/`
- Usuario actual: `/api/auth/me/`

El token se almacena en `localStorage`.

---

## 👤 Crear usuarios

```bash
docker exec -it church_backend python manage.py createsuperuser
```

---

En caso de validar rol en vistas:
```bash
if (user.role !== 'PASTOR') {
    alert("No autorizado")
    return
}
```

En caso de validar rol en clases o funciones:
```bash
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsPastor

class EventoView(APIView):
    permission_classes = [IsAuthenticated, IsPastor]

    def get(self, request):
        return Response({"ok": True})
```

---

# 📌 Autor

Proyecto interno para gestión de iglesia.
