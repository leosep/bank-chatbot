import os
import json
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from models import User, Call
import re
from sqlalchemy import or_

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database Configuration (for MariaDB)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://chatbot:123456@localhost/chatbot_db' # Replace with your MariaDB credentials
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'ABCABC123'
app.config['DEBUG'] = False

db.init_app(app)

LOG_FILE = "../backend/request_log.json"

# Create a simple list of predefined users for demonstration
PREDEFINED_USERS = {
    'bankagent1': 'bankpass123',
    'bankagent2': 'securebank',
}

def create_predefined_users():
    with app.app_context():
        # Check if the tables exist and create them if not
        db.create_all()
        for username, password in PREDEFINED_USERS.items():
            user = User.query.filter_by(username=username).first()
            if not user:
                # Change this line
                hashed_password = generate_password_hash(password) # Remove the method argument
                new_user = User(username=username, password=hashed_password)
                db.session.add(new_user)
        db.session.commit()
        print("Predefined users have been added to the database.")

@app.before_request
def require_login():
    allowed_routes = ['login', 'static', 'api_schedule_call', 'dashboard_stats', 'get_stats']
    if request.endpoint not in allowed_routes and 'logged_in' not in session:
        return redirect(url_for('login'))
    
# --- Login and Logout ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials. Please try again.'
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))

# --- Main Dashboard ---
@app.route('/')
def dashboard():
    return render_template('dashboard.html', username=session['username'])

# --- Call Management Module ---
@app.route('/calls')
def call_manager():
    try:
        # Parámetros de paginación y búsqueda
        page = request.args.get('page', 1, type=int)
        per_page = 20  # O el número que prefieras
        search_query = request.args.get('q', '').lower()
        
        # Filtros adicionales
        status_filter = request.args.get('status', 'all').lower()

        # Obtener todas las llamadas
        query = Call.query

        # Filtrar por estado si no es 'all'
        if status_filter != 'all':
            query = query.filter_by(status=status_filter.capitalize())
        
        # Filtrar por término de búsqueda
        if search_query:
            # Importa 'or_' si no lo has hecho: from sqlalchemy import or_
            query = query.filter(or_(
                Call.full_name.ilike(f'%{search_query}%'),
                Call.sender_id.ilike(f'%{search_query}%'),
                Call.phone.ilike(f'%{search_query}%'),
                Call.resolution.ilike(f'%{search_query}%')
            ))

        # Ordenar por fecha de creación de forma descendente y paginar
        calls_pagination = query.order_by(Call.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        
        # Datos para el frontend
        paginated_calls = calls_pagination.items
        total_pages = calls_pagination.pages
        total_items = calls_pagination.total

    except Exception as e:
        print(f"Error al cargar las llamadas: {e}")
        paginated_calls = []
        total_pages = 0
        total_items = 0
        search_query = ''
        status_filter = 'all'

    return render_template(
        'call_manager.html',
        calls=paginated_calls,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        search_query=search_query,
        status_filter=status_filter
    )

@app.route('/calls/update/<int:call_id>', methods=['POST'])
def update_call_status(call_id):
    call = Call.query.get_or_404(call_id)
    new_status = request.form.get('status')
    resolution = request.form.get('resolution')

    call.status = new_status
    if new_status == 'Resolved' and not call.resolved_at:
        call.resolved_at = datetime.utcnow()
    
    if resolution:
        call.resolution = resolution
    
    db.session.commit()
    return redirect(url_for('call_manager'))
    
# --- Log Viewer Module ---
@app.route('/logs')
def log_viewer():
    try:
        if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
            logs = []
        else:
            with open(LOG_FILE, 'r') as f:
                logs = json.load(f)

        # Parámetros de paginación y búsqueda
        page = request.args.get('page', 1, type=int)
        per_page = 20 # Número de registros por página
        search_query = request.args.get('q', '').lower()

        # Filtrar los registros si hay una búsqueda
        if search_query:
            filtered_logs = [
                log for log in logs
                if search_query in log.get('sender_id', '').lower() or
                    search_query in log.get('question', '').lower() or
                    search_query in log.get('answer', '').lower() or
                    search_query in log.get('category', '').lower()
            ]
        else:
            filtered_logs = logs

        # Ordenar los registros por fecha de forma descendente
        filtered_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Calcular los índices para la paginación
        total_items = len(filtered_logs)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_logs = filtered_logs[start:end]
        
        # Datos para el frontend
        total_pages = (total_items + per_page - 1) // per_page
        
    except (json.JSONDecodeError, FileNotFoundError):
        paginated_logs = []
        total_items = 0
        total_pages = 0
        search_query = ''
        page = 1

    return render_template(
        'log_viewer.html',
        logs=paginated_logs,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        search_query=search_query
    )

# --- NUEVO: Dashboard de Estadísticas ---
@app.route('/dashboard/stats')
def dashboard_stats():
    return render_template('dashboard_stats.html')

# --- Enlace a Whatsapp ---
@app.route('/whatsapp_link')
def whatsapp_link():
    return render_template('whatsapp_link.html')

@app.route('/dashboard/statsdata', methods=['GET'])
def get_stats():
    # Get filter parameters from the request
    filter_type = request.args.get('filter', 'daily')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date = None
    end_date = None

    if filter_type == 'daily':
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif filter_type == 'weekly':
        end_date = datetime.now() + timedelta(days=1)
        start_date = end_date - timedelta(days=7)
    elif filter_type == 'monthly':
        end_date = datetime.now() + timedelta(days=1)
        start_date = end_date - timedelta(days=30)
    elif filter_type == 'custom' and start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
    
    # Print dates to help with debugging
    print(f"Filtering logs from {start_date} to {end_date}")

    # 1. Calls data
    call_query = db.session.query(Call)
    if start_date and end_date:
        call_query = call_query.filter(Call.created_at.between(start_date, end_date))
    
    calls = call_query.all()
    
    call_status_counts = {
        'Pending': 0,
        'In Progress': 0,
        'Resolved': 0
    }
    for call in calls:
        if call.status in call_status_counts:
            call_status_counts[call.status] += 1
    
    # 2. Logs data
    try:
        if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
            logs = []
        else:
            with open(LOG_FILE, 'r') as f:
                logs = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logs = []
    
    # Filter logs by date range if provided
    filtered_logs = []
    if start_date and end_date:
        # Check if start_date has timezone info, if not, assume UTC for comparison
        if start_date.tzinfo is None:
            # You might need to adjust this depending on your server's timezone
            # For this example, let's assume logs are in UTC
            aware_start_date = start_date.replace(tzinfo=timezone.utc)
            aware_end_date = end_date.replace(tzinfo=timezone.utc)
        else:
            aware_start_date = start_date
            aware_end_date = end_date
        
        for log in logs:
            if 'timestamp' in log:
                try:
                    # FIX: Use datetime.fromisoformat() to handle the full timestamp
                    log_timestamp = datetime.fromisoformat(log['timestamp'])
                    
                    # Check if the log's timestamp falls within the specified range
                    if aware_start_date <= log_timestamp < aware_end_date:
                        filtered_logs.append(log)
                except ValueError:
                    # Skips logs with a bad timestamp format, but prints a message for debugging
                    print(f"Skipping log with invalid timestamp format: {log.get('timestamp')}")
                    continue
    
    # Aggregate log data
    log_category_counts = {}
    for log in filtered_logs:
        category = log.get('category', 'unknown')
        if category in log_category_counts:
            log_category_counts[category] += 1
        else:
            log_category_counts[category] = 1

    # Additional metric: average resolution time for calls
    resolved_calls = [call for call in calls if call.status == 'Resolved' and call.resolved_at]
    total_resolution_time = sum([
        (call.resolved_at - call.created_at).total_seconds()
        for call in resolved_calls
    ])
    avg_resolution_time = total_resolution_time / len(resolved_calls) if resolved_calls else 0
    
    # Prepare data for charts
    stats = {
        'call_status_data': list(call_status_counts.values()),
        'call_status_labels': list(call_status_counts.keys()),
        'log_category_data': list(log_category_counts.values()),
        'log_category_labels': list(log_category_counts.keys()),
        'total_calls': len(calls),
        'total_logs': len(filtered_logs),
        'avg_resolution_time_seconds': avg_resolution_time
    }

    return jsonify(stats)

# --- API Endpoint for the Chatbot ---
@app.route('/api/schedule_call', methods=['POST'])
def api_schedule_call():
    data = request.json
    sender_id = data.get('sender', 'unknown')
    full_name = data.get('full_name')
    phone = data.get('phone')
    preferred_time = data.get('preferred_time')

    if not all([full_name, phone, preferred_time]):
        return jsonify({'message': 'Missing required fields'}), 400

    new_call = Call(
        sender_id=sender_id,
        full_name=full_name,
        phone=phone,
        preferred_time=preferred_time
    )
    db.session.add(new_call)
    db.session.commit()
    
    return jsonify({'message': 'Call scheduled successfully'}), 201

if __name__ == '__main__':
    with app.app_context():
        create_predefined_users()
    app.run(debug=True, port=8000) # Run this on a different port than your backend API
