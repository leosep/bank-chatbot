import re
import requests
import fitz # PyMuPDF
import faiss
import numpy as np
import os
import json
from datetime import datetime
import pyodbc
from flask import Flask, request, jsonify
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sentence_transformers import SentenceTransformer
import mysql.connector
from sentence_transformers import SentenceTransformer
import openai
from openai import OpenAI
import MySQLdb

app = Flask(__name__)

# --- Configuración ---
# Puedes mover las credenciales a un archivo .env si lo prefieres para mayor seguridad
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "1234567890abcdef1234567890abcdef")
client = OpenAI(api_key=OPENAI_API_KEY)
LOG_FILE = "request_log.json"

# --- Configuración de la Base de Datos SQL Server (para datos de empleados) ---
DB_CONFIG_SQL = {
    'driver': '{ODBC Driver 17 for SQL Server}',
    'server': '123.123.123.123',
    'database': 'bank_db',
    'uid': 'ChatBot',
    'pwd': '123456'
}

# --- Configuración de la Base de Datos MySQL (para gestión de sesiones) ---
DB_URI_MYSQL = 'mysql+mysqlconnector://chatbot:123456@localhost/chatbot_db'
# Se añade pool_recycle para evitar el error de "Broken pipe"
engine = create_engine(DB_URI_MYSQL, pool_recycle=3600)
Base = declarative_base()

# Definición del modelo de la tabla para las sesiones
class UserSession(Base):
    __tablename__ = 'user_sessions'
    sender_id = Column(String(255), primary_key=True)
    employee_id = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False)
    last_active = Column(DateTime, default=datetime.utcnow)
    awaiting_code = Column(Boolean, default=False)
    provided_cedula = Column(String(255), nullable=True)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# --- Procesamiento e Incrustación de PDF ---
text_chunks = []
docs_dir = "docs/"
pdf_files = [os.path.join(docs_dir, f) for f in os.listdir(docs_dir) if f.endswith(".pdf")]

if not pdf_files:
    print("Advertencia: No se encontraron archivos PDF en el directorio 'docs/'.")
    text_chunks = ["No se pudo cargar el documento PDF o procesar la información. Por favor, contacte a soporte."]
else:
    for pdf_path in pdf_files:
        try:
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    page_text = page.get_text()
                    lines = page_text.split('\n')
                    for line in lines:
                        stripped_line = line.strip()
                        if len(stripped_line) > 20:
                            text_chunks.append(stripped_line)
        except Exception as e:
            print(f"Error al procesar el PDF {pdf_path}: {e}")
            text_chunks.append(f"Error al cargar información de {os.path.basename(pdf_path)}.")

if not text_chunks:
    text_chunks = ["No se pudo cargar el documento PDF o procesar la información. Por favor, contacte a soporte."]

try:
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(text_chunks)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings))
    print(f"Cargados {len(text_chunks)} fragmentos de texto de todos los PDFs y creado el índice FAISS.")
except Exception as e:
    print(f"Error al generar incrustaciones: {e}")
    text_chunks = ["No se pudo procesar la información para el chatbot."]
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(text_chunks)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings))
    
# --- Funciones de Ayuda ---
def get_db_connection_sql():
    """Establece una conexión a la base de datos SQL Server para datos de empleados."""
    conn_str = (
        f"DRIVER={DB_CONFIG_SQL['driver']};"
        f"SERVER={DB_CONFIG_SQL['server']};"
        f"DATABASE={DB_CONFIG_SQL['database']};"
        f"UID={DB_CONFIG_SQL['uid']};"
        f"PWD={DB_CONFIG_SQL['pwd']};"
    )
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"Error de conexión a la base de datos SQL Server: {sqlstate} - {ex}")
        return None

def get_session(sender_id):
    """Recupera el estado de la sesión del usuario desde memoria."""
    return user_sessions.get(sender_id, {'employee_id': None, 'verified': False, 'awaiting_code': False, 'provided_cedula': None})

def save_session(sender_id, employee_id, is_verified, awaiting_code=False, provided_cedula=None):
    """Guarda o actualiza el estado de la sesión en memoria y archivo."""
    user_sessions[sender_id] = {
        'employee_id': employee_id,
        'verified': is_verified,
        'awaiting_code': awaiting_code,
        'provided_cedula': provided_cedula
    }
    # Save to file
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(user_sessions, f)
    except Exception as e:
        print(f"Error saving sessions to file: {e}")

def verify_employee_identity(cedula, employee_code):
    """
    Verifica la identidad del empleado contra la base de datos RRHH (SQL Server).
    Devuelve el employee_id si se verifica, None en caso contrario.
    """
    conn = get_db_connection_sql()
    if conn:
        try:
            cursor = conn.cursor()
            query = "SELECT employee_id FROM employees WHERE cedula = ? AND employee_id = ?"
            cursor.execute(query, (cedula, int(employee_code, base=10)))
            result = cursor.fetchone()
            if result:
                print(f"Empleado {cedula} verificado.")
                return result[0]
            else:
                print(f"Verificación fallida para Cédula: {cedula}, Código: {employee_code}")
                return None
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Error de consulta SQL durante la verificación: {sqlstate} - {ex}")
            return None
        finally:
            conn.close()
    return None

def get_employee_data(employee_id):
    """
    Recupera datos específicos del empleado de la base de datos SQL Server.
    """
    conn = get_db_connection_sql()
    if conn:
        try:
            cursor = conn.cursor()
            query = "SELECT hire_date FROM employees WHERE employee_id = ?"
            cursor.execute(query, (employee_id,))
            result = cursor.fetchone()
            if result:
                return {"hire_date": result[0].strftime("%Y-%m-%d")}
            else:
                return {}
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Error de consulta SQL durante la recuperación de datos: {sqlstate} - {ex}")
            return {}
        finally:
            conn.close()
    return {}

def get_session_from_mysql(sender_id):
    """Recupera el estado de la sesión del usuario desde MySQL."""
    session = Session()
    try:
        user_session = session.query(UserSession).filter_by(sender_id=sender_id).first()
        if user_session:
            return {
                'employee_id': user_session.employee_id,
                'verified': user_session.is_verified,
                'awaiting_code': user_session.awaiting_code,
                'provided_cedula': user_session.provided_cedula
            }
        return {'employee_id': None, 'verified': False, 'awaiting_code': False, 'provided_cedula': None}
    except Exception as e:
        print(f"Error al leer la sesión desde MySQL: {e}")
        return {'employee_id': None, 'verified': False, 'awaiting_code': False, 'provided_cedula': None}
    finally:
        session.close()

def save_session_to_mysql(sender_id, employee_id, is_verified, awaiting_code=False, provided_cedula=None):
    """Guarda o actualiza el estado de la sesión en MySQL."""
    session = Session()
    try:
        user_session = session.query(UserSession).filter_by(sender_id=sender_id).first()
        if user_session:
            user_session.employee_id = employee_id
            user_session.is_verified = is_verified
            user_session.last_active = datetime.utcnow()
            user_session.awaiting_code = awaiting_code
            user_session.provided_cedula = provided_cedula
        else:
            new_session = UserSession(
                sender_id=sender_id,
                employee_id=employee_id,
                is_verified=is_verified,
                last_active=datetime.utcnow(),
                awaiting_code=awaiting_code,
                provided_cedula=provided_cedula
            )
            session.add(new_session)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Error al guardar la sesión en MySQL: {e}")
    finally:
        session.close()

def get_employee_name(employee_id):
    """
    Recupera el nombre del empleado de la base de datos SQL Server.
    """
    conn = get_db_connection_sql()
    if conn:
        try:
            cursor = conn.cursor()
            query = "SELECT CONCAT(first_name, ' ', last_name) AS nombre_empleado FROM employees WHERE employee_id = ?"
            cursor.execute(query, (employee_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return "Colaborador"
        except pyodbc.Error as ex:
            sqlstate = ex.args[0]
            print(f"Error de consulta SQL durante la recuperación del nombre: {sqlstate} - {ex}")
            return "Colaborador"
        finally:
            conn.close()
    return "Colaborador"

def search_similar_chunks(question, k=4):
    """Busca fragmentos de texto similares en las incrustaciones del PDF."""
    if not text_chunks:
        return "No hay información disponible del documento."
    q_embed = model.encode([question])
    D, I = index.search(np.array(q_embed), k=k)
    return "\n".join([text_chunks[i] for i in I[0]])

def log_request(sender_id, question, answer, category="General", employee_id=None):
    """Registra cada solicitud en un archivo JSON."""
    log_entry = {
        "timestamp": datetime.now(ZoneInfo("America/Santo_Domingo")).isoformat(),
        "sender_id": sender_id,
        "employee_id": employee_id,
        "question": question,
        "answer": answer,
        "category": category
    }
    try:
        data = []
        if os.path.exists(LOG_FILE):
            if os.path.getsize(LOG_FILE) > 0:
                with open(LOG_FILE, 'r+') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        print(f"Advertencia: El archivo de log '{LOG_FILE}' está vacío o corrupto. Se inicializará con un nuevo contenido.")
                        data = []
        if not isinstance(data, list):
            data = []
        data.append(log_entry)
        with open(LOG_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error al registrar la solicitud: {e}")
        
def get_request_history(sender_id):
    """Recupera el historial de solicitudes para un remitente específico."""
    history = []
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                data = json.load(f)
                history = [entry for entry in data if entry["sender_id"] == sender_id]
    except Exception as e:
        print(f"Error al leer el archivo de registro para el historial: {e}")
    return history

def count_requests_by_category():
    """Cuenta las solicitudes por categoría."""
    category_counts = {}
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                data = json.load(f)
                for entry in data:
                    category = entry.get("category", "Uncategorized")
                    category_counts[category] = category_counts.get(category, 0) + 1
    except Exception as e:
        print(f"Error al contar las solicitudes por categoría: {e}")
    return category_counts

def format_openai_response(response):
    """Formatea la respuesta de OpenAI: añade emoticons, separa listas, evita párrafos largos."""
    # Replace long paragraphs with shorter lines
    response = response.replace('\n\n', '\n')
    # Add emoticons randomly or based on content
    if 'vacaciones' in response.lower():
        response = '🏖️ ' + response
    elif 'licencia' in response.lower():
        response = '📋 ' + response
    elif 'pago' in response.lower():
        response = '💰 ' + response
    # Separate lists: assume if has 1. 2. etc, keep, else if comma separated, make bullets
    if ',' in response and not re.search(r'\d+\.', response):
        items = [item.strip() for item in response.split(',')]
        if len(items) > 1:
            response = '\n'.join(f'- {item}' for item in items)
    return response

# --- Rutas de Flask ---
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    q = data.get("question", "")
    sender_id = data.get("sender", "unknown_sender")
    
    if not q:
        return jsonify({"answer": "Por favor, haz una pregunta."}), 400

    # Obtener el estado de la sesión desde MySQL
    session_data = get_session_from_mysql(sender_id)
    employee_id = session_data.get('employee_id')
    is_verified = session_data.get('verified', False)

    lower_q = q.lower().strip()
    response_text = ""
    category = "General"

    # --- Flujo de Verificación de Identidad ---
    if not is_verified:
        session_data = get_session_from_mysql(sender_id)
        awaiting_code = session_data.get('awaiting_code', False)
        provided_cedula = session_data.get('provided_cedula')

        if awaiting_code and provided_cedula:
            # Expecting employee code
            code_match = re.search(r'\b(\d{3,})\b', lower_q)
            if code_match:
                employee_code = code_match.group(1).strip()
                verified_id = verify_employee_identity(provided_cedula, employee_code)
                if verified_id:
                    employee_name = get_employee_name(verified_id)
                    save_session_to_mysql(sender_id, verified_id, True, awaiting_code=False, provided_cedula=None)
                    employee_id = verified_id
                    response_text = f"🎉 ¡Bienvenido, {employee_name}! 🎉\nTu identidad ha sido verificada. ¿En qué puedo ayudarte hoy?"
                    category = "Identity Verification Success"
                else:
                    save_session_to_mysql(sender_id, None, False, awaiting_code=False, provided_cedula=None)
                    response_text = "❌ Lo siento, no pude verificar tu identidad.\n\nPor favor, asegúrate de que tu Cédula y Código de Empleado sean correctos e inténtalo de nuevo."
                    category = "Identity Verification Failed"
            else:
                response_text = "Por favor, proporciona tu código de empleado."
                category = "Identity Prompt - Code"
        else:
            # Ask for cedula
            digits = re.findall(r'\d', lower_q)
            if len(digits) >= 11:
                cedula_raw = ''.join(digits[:11])
                cedula = f"{cedula_raw[:3]}-{cedula_raw[3:10]}-{cedula_raw[10]}"
                save_session_to_mysql(sender_id, None, False, awaiting_code=True, provided_cedula=cedula)
                response_text = "Gracias. Ahora, por favor proporciona tu código de empleado."
                category = "Identity Prompt - Cedula Provided"
            else:
                response_text = "👋 ¡Hola! Soy tu Asistente virtual Banco.\n\nPara poder apoyarte, primero necesito verificar tu identidad. Por favor, comparte tu Cédula."
                category = "Welcome/Identity Prompt"

        log_request(sender_id, q, response_text, category, employee_id)
        return jsonify({"answer": response_text})

    # --- Si la identidad está verificada, proceder con otras solicitudes ---
    if "hola" in lower_q or "saludos" in lower_q:
        response_text = "👋 ¡Hola! Soy tu Asistente virtual Banco.\n\nEstamos por esta vía para apoyarte. ¿En qué puedo ayudarte hoy?"
        category = "Welcome"
    elif "certificado de empleo" in lower_q or "carta de trabajo" in lower_q:
        response_text = "📄 Solicitud de Certificado de Empleo\n\nPuedes hacerlo directamente desde el Sistema Interno.\n\nPasos:\n1. Ingresa con tu usuario y contraseña.\n2. Selecciona la opción Recursos Humanos.\n3. Elige Certificado de Empleo y completa la información solicitada.\n\n¡Listo! 😊"
        category = "Certificado de Empleo"
    elif "tiempo libre" in lower_q or "vacaciones" in lower_q:
        if "pago" in lower_q or "no me han pagado" in lower_q:
            response_text = "💰 Pago de Beneficios de Descanso\n\nEl pago se realiza cada año según fecha de ingreso.\nPuedes revisar en Sistema Interno > Mis Pagos.\nSi no aparece, responde 'RECLAMO BENEFICIOS'."
            category = "Beneficios - Pago"
        else:
            employee_data = get_employee_data(employee_id)
            nueva_fecha = ""
            if employee_data and employee_data.get('hire_date'):
                try:
                    fecha_obj = datetime.strptime(employee_data['hire_date'], "%Y-%m-%d")
                    nueva_fecha = fecha_obj + relativedelta(years=1)
                    hire_date_info = f" el día {nueva_fecha.strftime('%d de %B de %Y')}"
                except ValueError:
                    hire_date_info = f" el día {employee_data['hire_date']}"
            response_text = f"🏖️ Beneficios de Descanso\n\nCumples beneficios{hire_date_info}.\nTienes 14 días para disfrutar y pagar cada año.\nCon 5 años en adelante son 18 días pagados + 14 días de disfrute.\n\nPara solicitar:\n1. Ve al Sistema Interno.\n2. Ingresa con tu usuario y contraseña.\n3. Selecciona Solicitud de Beneficios.\n4. Completa la información.\n\nSi necesitas ayuda con el Sistema Interno, responde 'AYUDA SISTEMA'.\nDebe estar aprobado por tu supervisor.\nSe genera automáticamente tras aprobación."
            category = "Beneficios de Descanso"
    elif "permiso" in lower_q or "licencia" in lower_q:
        if "nacimiento" in lower_q:
            response_text = "👶 Permiso por Nacimiento\n\n2 días laborables pagados.\nTraer el Acta de nacimiento del bebé.\nRecuerda compartir la justificación con el supervisor."
            category = "Permisos - Nacimiento"
        elif "fallecimiento" in lower_q:
            response_text = "🙏 Permiso por Fallecimiento\n\n3 días laborables pagados por la empresa.\nPor fallecimiento de madre, padre, hijos, abuelos o cónyuge.\nTraer el Acta de defunción.\nRecuerda compartir la justificación con el supervisor."
            category = "Permisos - Fallecimiento"
        elif "matrimonio" in lower_q:
            response_text = "💍 Permiso por Matrimonio\n\n5 días laborables pagados.\nTraer el Acta de matrimonio.\nRecuerda compartir la justificación con el supervisor."
            category = "Permisos - Matrimonio"
        else:
            response_text = "📋 Tipos de Permisos\n\nSegún el Código Laboral de la República Dominicana:\n- Nacimiento de hijo: 2 días\n- Fallecimiento (madre, padre, hijos, abuelos, cónyuge): 3 días\n- Matrimonio: 5 días\n\nRecuerda compartir la justificación con el supervisor."
            category = "Permisos - General"
    elif "faltan horas" in lower_q or "salario" in lower_q or "falta de horas" in lower_q:
        response_text = "⏰ Horas Faltantes en Salario\n\nPor favor indícanos:\n- Puesto de Servicio y turno\n- Día pendiente\n- Cantidad de Horas faltantes\n\nEl equipo revisará el caso y te contactará en un máximo de 48 horas."
        category = "Salario - Horas Faltantes"
    elif "descuento no reconocido" in lower_q:
        response_text = "💸 Descuento No Reconocido\n\nPuedes ver tus descuentos en Sistema Interno > Mis Pagos.\nSi crees que hay un error, responde con 'RECLAMO DESCUENTO'.\nNuestro equipo validará la información pronto."
        category = "Salario - Descuento"
    elif "fecha de pago" in lower_q or "cuando pagan" in lower_q:
        response_text = "📅 Fechas de Pago de Salario\n\n- Horas del 29 al 13: pagan el día 21 del mismo mes.\n- Horas del 14 al 28: pagan el día 6 del siguiente mes."
        category = "Fecha de Pago"
    elif "préstamos" in lower_q or "prestamos" in lower_q:
        response_text = "💳 Préstamos\n\nEstamos trabajando para mejorar y aperturar este servicio.\nEste canal está disponible 24 horas con tu Asistente Virtual Banco.\n¡Gracias por contactarte!"
        category = "Préstamos"
    elif any(phrase in lower_q for phrase in ["agendar", "llamada", "hablar con alguien", "contactar representante", "necesito ayuda", "quiero hablar", "llamenme", "comunicarme"]):
        # Use name from DB, extract and format phone from sender_id, time as ASAP
        employee_name = get_employee_name(employee_id)
        phone_raw = sender_id.split('@')[0]  # Extract phone number
        # Format phone: remove leading 1 if 11 digits, then XXX-XXX-XXXX
        if phone_raw.startswith('1') and len(phone_raw) == 11:
            phone_raw = phone_raw[1:]
        if len(phone_raw) == 10:
            phone = f"{phone_raw[:3]}-{phone_raw[3:6]}-{phone_raw[6:]}"
        else:
            phone = phone_raw  # Fallback
        preferred_time = "Lo antes posible"

        try:
            requests.post('http://localhost:8000/api/schedule_call', json={
                'sender': sender_id,
                'full_name': employee_name,
                'phone': phone,
                'preferred_time': preferred_time
            })
            response_text = f"✅ ¡Perfecto, {employee_name}! Hemos agendado tu solicitud para una llamada.\nUn representante se pondrá en contacto contigo lo antes posible.\nGracias por contactarte con BancoBot!"
            category = "Agendar Llamada - Success"
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to the call management backend: {e}")
            response_text = "❌ Lo siento, no pude agendar la llamada en este momento.\nPor favor, inténtalo más tarde."
            category = "Agendar Llamada - Error"
    elif "ayuda sistema" in lower_q or "ayuda rrhh" in lower_q:
        response_text = "🖥️ Ayuda con Sistema Interno\n\nPuedes consultar los instructivos o enlaces proporcionados.\nSi aún necesitas asistencia, podemos agendar una llamada."
        category = "Sistema Interno Help"
    elif "comprobante de pagos" in lower_q:
        response_text = "📄 Comprobante de Pagos\n\nPuedes ver tus comprobantes en Sistema Interno > Mis Pagos."
        category = "Comprobante de Pagos"
    elif "prestaciones" in lower_q:
        response_text = "🎁 Prestaciones\n\nPara información, completa el formulario con:\n- Nombre\n- Cédula\n- Teléfono\n- Código RRHH\n\nEsto nos ayudará a asistirte adecuadamente."
        category = "Prestaciones"
    else:
        context = search_similar_chunks(q)

        # Nuevo prompt con instrucciones más estrictas para no salirse del tema
        prompt = f"Eres un asistente virtual llamado 'Banco Assistant', cuyo único objetivo es responder preguntas basadas **estrictamente** en el siguiente manual proporcionado.\nSi la pregunta no se puede responder con la información del manual, debes decir que no tienes información al respecto y ofrecer agendar una llamada. **No utilices conocimiento externo**. El manual de referencia es:\n\n{context}\n\nPregunta: {q}\n\nRespuesta:"
        try:
            chat_completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5 # Bajar la temperatura para respuestas más directas
            )
            response_text = chat_completion.choices[0].message.content.strip()
            category = "OpenAI - General"
            if "no puedo responder" in response_text.lower() or "no tengo información" in response_text.lower() or "no encontré información" in response_text.lower():
                response_text = "No tengo información al respecto. Si necesitas más ayuda, puedo agendar una llamada con un representante."
                category = "OpenAI - Referral"
            else:
                # Format the response: add emoticons, bold, separate lists
                response_text = format_openai_response(response_text)
        except Exception as e:
            print(f"Error con la API de OpenAI: {e}")
            response_text = "❌ Disculpa, no pude obtener una respuesta en este momento.\nPor favor, intenta de nuevo o agenda una llamada con un representante."
            category = "OpenAI - Error"
        
    log_request(sender_id, q, response_text, category, employee_id)
    return jsonify({"answer": response_text})

@app.route("/history/<sender_id>", methods=["GET"])
def get_history(sender_id):
    history = get_request_history(sender_id)
    return jsonify({"history": history})

@app.route("/counts", methods=["GET"])
def get_counts():
    counts = count_requests_by_category()
    return jsonify({"category_counts": counts})

if __name__ == "__main__":
    app.run(port=5000, debug=True)