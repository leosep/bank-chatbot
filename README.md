# BancoBot

This project is a complete WhatsApp chatbot system developed for bank employees, including an automated bot, a Python backend API, and a web portal for agents.

## Features

### WhatsApp Bot
- WhatsApp Web integration using Baileys (@whiskeysockets/baileys)
- Automated message processing
- Support for multiple user sessions
- Logging of all interactions
- Web interface for device linking (port 3000)

### Backend API
- REST API built with Flask
- Integration with AI models (OpenAI GPT-4o-mini)
- Semantic search in PDF documents using FAISS and Sentence Transformers
- User session management in MySQL
- Employee identity verification against SQL Server database
- JSON request logging
- Endpoint for scheduling calls

### Agent Web Portal
- Responsive web interface with Flask
- User authentication system
- Main dashboard
- Call management (create, update, filter)
- Log viewer with pagination and search
- Dashboard statistics with charts
- WhatsApp link (integrated iframe)
- Modern theme with Font Awesome

### Database
- MariaDB for persistent storage of the web portal (users and calls)
- MySQL for chatbot sessions
- SQL Server for employee data

## Project Structure

```
bankbot/
├── .gitignore                 # Git ignored files
├── package.json               # Node.js dependencies
├── package-lock.json          # Node.js lockfile
├── whatsapp_bot.js            # Main WhatsApp bot
├── backend/                   # Python backend API
│   ├── app_openai_api.py      # Main API with OpenAI
│   ├── requirements.txt       # Python dependencies
│   ├── request_log.json       # Request logs
│   └── docs/                  # Directory for PDF documents
├── web/                       # Agent web portal
│   ├── app.py                 # Flask application
│   ├── database.py            # Database configuration
│   ├── models.py              # SQLAlchemy models
│   ├── requirements.txt       # Python dependencies
│   ├── static/                # Static files (CSS, JS)
│   └── templates/             # HTML templates
│       ├── base.html          # Base template
│       ├── login.html         # Login page
│       ├── dashboard.html     # Main dashboard
│       ├── call_manager.html  # Call management
│       ├── log_viewer.html    # Log viewer
│       ├── dashboard_stats.html # Statistics
│       └── whatsapp_link.html # WhatsApp link
```

## System Requirements

- Node.js (version 14 or higher)
- Python 3.8+
- MariaDB
- MySQL
- SQL Server (for employee data)
- npm or yarn

## Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd bancobot
```

### 2. Install Node.js dependencies
```bash
npm install
```

### 3. Install Python dependencies
```bash
cd backend
pip install -r requirements.txt
cd ../web
pip install -r requirements.txt
```

### 4. Configure databases
- Create a MariaDB database named `chatbot_db`
- Create a MySQL database named `chatbot_db` (for sessions)
- Configure credentials in `web/app.py` and `backend/app_openai_api.py`
- Ensure access to SQL Server database with employee data

### 5. Configure environment variables
- Set `OPENAI_API_KEY` in environment or in `backend/app_openai_api.py`
- Place PDF documents in `backend/docs/` for semantic search

## Usage

### WhatsApp Device Linking
```bash
node whatsapp_bot.js
```
Access `http://localhost:3000` to scan the QR code and link the device.

### Start Backend API
```bash
cd backend
python app_openai_api.py
```

### Start Web Portal
```bash
cd web
python app.py
```

The web portal will be available at `http://localhost:8000`

## Portal Features

### Authentication
- Login with predefined username and password
- Secure sessions

### Dashboard
- System overview
- Intuitive navigation

### Call Management
- Paginated call list
- Filters by status and search
- Call status updates
- Creation of new calls

### Log Viewer
- Chatbot interaction logs
- Pagination and search filters
- Detailed information for each message

### Statistics
- Call status charts
- Log categories
- Average resolution time

### WhatsApp Link
- Integrated WhatsApp interface iframe
- Direct access from the portal

## API Endpoints

### Backend API (port 5000)
- `POST /ask`: Process chatbot messages
- `GET /history/<sender_id>`: Get user history
- `GET /counts`: Count requests by category

### Web API (port 8000)
- `POST /api/schedule_call`: Schedule calls from web
- `GET /dashboard/statsdata`: Statistics data

## Configuration

### Predefined Users
- bankagent1: bankpass123
- bankagent2: securebank

### Environment Variables
- `OPENAI_API_KEY`: OpenAI API key

### Databases
- MariaDB: Configure URI in `web/app.py`
- MySQL: Configure URI in `backend/app_openai_api.py`
- SQL Server: Configure credentials in `backend/app_openai_api.py`

## Development

### Adding New Features
1. For backend: Modify `backend/app_openai_api.py`
2. For web: Modify `web/app.py` and templates
3. For bot: Modify `whatsapp_bot.js`

### Logs
- Backend logs are saved in `backend/request_log.json`
- Web logs are displayed in the log viewer

## Deployment

1. Configure servers with Node.js and Python
2. Install MariaDB, MySQL, and SQL Server
3. Copy project files
4. Configure environment variables and databases
5. Start services in order: Databases, backend, web, bot
