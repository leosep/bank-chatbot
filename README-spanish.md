# BankBot

Este proyecto es un sistema completo de chatbot para WhatsApp desarrollado para empleados de banco, que incluye un bot automatizado, una API backend en Python y un portal web para agentes.

## Características

### Bot de WhatsApp
- Integración con WhatsApp Web usando Baileys (@whiskeysockets/baileys)
- Procesamiento de mensajes automatizado
- Soporte para múltiples sesiones de usuario
- Logging de todas las interacciones
- Interfaz web para vinculación de dispositivo (puerto 3000)

### API Backend
- API REST construida con Flask
- Integración con modelos de IA (OpenAI GPT-4o-mini)
- Búsqueda semántica en documentos PDF usando FAISS y Sentence Transformers
- Gestión de sesiones de usuario en MySQL
- Verificación de identidad de empleados contra base de datos SQL Server
- Logging de solicitudes en JSON
- Endpoint para programar llamadas

### Portal Web para Agentes
- Interfaz web responsiva con Flask
- Sistema de autenticación de usuarios
- Dashboard principal
- Gestión de llamadas (crear, actualizar, filtrar)
- Visor de registros con paginación y búsqueda
- Estadísticas del dashboard con gráficos
- Enlace a WhatsApp (iframe integrado)
- Tema moderno con Font Awesome

### Base de Datos
- MariaDB para almacenamiento persistente del portal web (usuarios y llamadas)
- MySQL para sesiones de chatbot
- SQL Server para datos de empleados

## Estructura del Proyecto

```
bankbot/
├── .gitignore                 # Archivos ignorados por Git
├── package.json               # Dependencias Node.js
├── package-lock.json          # Lockfile de Node.js
├── whatsapp_bot.js            # Bot principal de WhatsApp
├── backend/                   # API backend en Python
│   ├── app_openai_api.py      # API principal con OpenAI
│   ├── requirements.txt       # Dependencias Python
│   ├── request_log.json       # Log de solicitudes
│   └── docs/                  # Directorio para documentos PDF
├── web/                       # Portal web para agentes
│   ├── app.py                 # Aplicación Flask
│   ├── database.py            # Configuración de base de datos
│   ├── models.py              # Modelos SQLAlchemy
│   ├── requirements.txt       # Dependencias Python
│   ├── static/                # Archivos estáticos (CSS, JS)
│   └── templates/             # Plantillas HTML
│       ├── base.html          # Plantilla base
│       ├── login.html         # Página de login
│       ├── dashboard.html     # Dashboard principal
│       ├── call_manager.html  # Gestión de llamadas
│       ├── log_viewer.html    # Visor de logs
│       ├── dashboard_stats.html # Estadísticas
│       └── whatsapp_link.html # Enlace a WhatsApp
```

## Requisitos del Sistema

- Node.js (versión 14 o superior)
- Python 3.8+
- MariaDB
- MySQL
- SQL Server (para datos de empleados)
- npm o yarn

## Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/leosep/bank-chatbot.git
cd bank-chatbot
```

### 2. Instalar dependencias de Node.js
```bash
npm install
```

### 3. Instalar dependencias de Python
```bash
cd backend
pip install -r requirements.txt
cd ../web
pip install -r requirements.txt
```

### 4. Configurar las bases de datos
- Crear una base de datos MariaDB llamada `chatbot_db`
- Crear una base de datos MySQL llamada `chatbot_db` (para sesiones)
- Configurar credenciales en `web/app.py` y `backend/app_openai_api.py`
- Asegurar acceso a base de datos SQL Server con datos de empleados

### 5. Configurar variables de entorno
- Establecer `OPENAI_API_KEY` en el entorno o en `backend/app_openai_api.py`
- Colocar documentos PDF en `backend/docs/` para la búsqueda semántica

## Uso

### Vinculación del Dispositivo WhatsApp
```bash
node whatsapp_bot.js
```
Acceder a `http://localhost:3000` para escanear el código QR y vincular el dispositivo.

### Iniciar la API Backend
```bash
cd backend
python app_openai_api.py
```

### Iniciar el Portal Web
```bash
cd web
python app.py
```

El portal web estará disponible en `http://localhost:8000`

## Funcionalidades del Portal

### Autenticación
- Login con usuario y contraseña predefinidos
- Sesiones seguras

### Dashboard
- Vista general del sistema
- Navegación intuitiva

### Gestión de Llamadas
- Lista paginada de llamadas
- Filtros por estado y búsqueda
- Actualización de estados de llamadas
- Creación de nuevas llamadas

### Visor de Registros
- Logs de interacciones del chatbot
- Paginación y filtros de búsqueda
- Información detallada de cada mensaje

### Estadísticas
- Gráficos de estado de llamadas
- Categorías de logs
- Tiempo promedio de resolución

### Enlace a WhatsApp
- Iframe integrado a la interfaz de WhatsApp
- Acceso directo desde el portal

## API Endpoints

### Backend API (puerto 5000)
- `POST /ask`: Procesar mensajes del chatbot
- `GET /history/<sender_id>`: Obtener historial de un usuario
- `GET /counts`: Contar solicitudes por categoría

### Web API (puerto 8000)
- `POST /api/schedule_call`: Programar llamadas desde web
- `GET /dashboard/statsdata`: Datos de estadísticas

## Configuración

### Usuarios Predefinidos
- bankagent1: bankpass123
- bankagent2: securebank

### Variables de Entorno
- `OPENAI_API_KEY`: Clave de API de OpenAI

### Bases de Datos
- MariaDB: Configurar URI en `web/app.py`
- MySQL: Configurar URI en `backend/app_openai_api.py`
- SQL Server: Configurar credenciales en `backend/app_openai_api.py`

## Desarrollo

### Agregar Nuevas Funcionalidades
1. Para el backend: Modificar `backend/app_openai_api.py`
2. Para el web: Modificar `web/app.py` y templates
3. Para el bot: Modificar `whatsapp_bot.js`

### Logs
- Los logs del backend se guardan en `backend/request_log.json`
- Los logs del web se muestran en el visor de registros

## Despliegue

1. Configurar servidores con Node.js y Python
2. Instalar MariaDB, MySQL y SQL Server
3. Copiar archivos del proyecto
4. Configurar variables de entorno y bases de datos
5. Iniciar servicios en orden: Bases de datos, backend, web, bot
