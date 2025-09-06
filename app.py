import os
import json
import uuid
import datetime
from flask import Flask, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
import requests

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'mp4', 'avi', 'mkv', 'mp3'}
SECRET_KEY = 'your-secret-key-here'  # Change this to a random secret key
BOT_TOKEN = '8107369635:AAE-1siL6UYG7VbyWkFD9mAJAeMczPVGNME'  # Replace with your bot token
OWNER_TELEGRAM_ID = '7711480832'  # Replace with your Telegram ID
TELEGRAM_API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# User database (in a real app, use a proper database)
USERS = {
    "admin": "password123"  # username: password
}

# Login logs storage
LOGIN_LOGS_FILE = 'login_logs.json'

# Files database (in a real app, use a proper database)
FILES_DB_FILE = 'files_db.json'

# Initialize files database if it doesn't exist
if not os.path.exists(FILES_DB_FILE):
    with open(FILES_DB_FILE, 'w') as f:
        json.dump([], f)

# Initialize login logs if it doesn't exist
if not os.path.exists(LOGIN_LOGS_FILE):
    with open(LOGIN_LOGS_FILE, 'w') as f:
        json.dump({}, f)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_client_ip():
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']

def send_telegram_notification(message):
    """Send notification to Telegram bot"""
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {
            "chat_id": OWNER_TELEGRAM_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")
        return False

def log_login(username):
    """Log successful login"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip_address = get_client_ip()
    
    # Load existing logs
    with open(LOGIN_LOGS_FILE, 'r') as f:
        logs = json.load(f)
    
    # Add new log
    if username not in logs:
        logs[username] = []
    
    logs[username].append({
        "timestamp": timestamp,
        "ip": ip_address
    })
    
    # Save logs
    with open(LOGIN_LOGS_FILE, 'w') as f:
        json.dump(logs, f)
    
    # Send notification to Telegram
    message = f"<b>Login Success</b>\n\nUsername: {username}\nTime: {timestamp}\nIP: {ip_address}"
    send_telegram_notification(message)

def generate_token():
    """Generate a random token"""
    return str(uuid.uuid4())

def get_files_db():
    """Get files database"""
    with open(FILES_DB_FILE, 'r') as f:
        return json.load(f)

def save_files_db(files_db):
    """Save files database"""
    with open(FILES_DB_FILE, 'w') as f:
        json.dump(files_db, f)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"success": False, "message": "Username dan password diperlukan"}), 400
    
    if username in USERS and USERS[username] == password:
        # Generate token
        token = generate_token()
        
        # Log successful login
        log_login(username)
        
        return jsonify({
            "success": True,
            "message": "Login berhasil",
            "token": token
        })
    else:
        return jsonify({"success": False, "message": "Username atau password salah"}), 401

@app.route('/api/upload', methods=['POST'])
def upload_file():
    # Check if token is valid
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"success": False, "message": "Token tidak valid"}), 401
    
    token = auth_header.split(' ')[1]
    
    # In a real app, you would validate the token here
    # For simplicity, we'll skip token validation
    
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Tidak ada file yang diupload"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"success": False, "message": "Tidak ada file yang dipilih"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Generate unique filename to avoid conflicts
        base, ext = os.path.splitext(filename)
        unique_filename = f"{base}_{uuid.uuid4().hex[:8]}{ext}"
        
        # Save file
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        file_type = file.mimetype or 'application/octet-stream'
        
        # Add to files database
        files_db = get_files_db()
        
        file_info = {
            "id": str(uuid.uuid4()),
            "name": filename,
            "filename": unique_filename,
            "size": file_size,
            "type": file_type,
            "upload_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        files_db.append(file_info)
        save_files_db(files_db)
        
        return jsonify({
            "success": True,
            "message": "File berhasil diupload",
            "file": file_info
        })
    
    return jsonify({"success": False, "message": "Tipe file tidak diizinkan"}), 400

@app.route('/api/files', methods=['GET'])
def list_files():
    # Check if token is valid
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"success": False, "message": "Token tidak valid"}), 401
    
    # In a real app, you would validate the token here
    # For simplicity, we'll skip token validation
    
    files_db = get_files_db()
    
    # Return files in reverse order (newest first)
    return jsonify({
        "success": True,
        "files": list(reversed(files_db))
    })

@app.route('/api/download/<file_id>', methods=['GET'])
def download_file(file_id):
    # Check if token is valid
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"success": False, "message": "Token tidak valid"}), 401
    
    # In a real app, you would validate the token here
    # For simplicity, we'll skip token validation
    
    files_db = get_files_db()
    
    # Find file
    file_info = None
    for file in files_db:
        if file['id'] == file_id:
            file_info = file
            break
    
    if not file_info:
        abort(404)
    
    file_path = os.path.join(UPLOAD_FOLDER, file_info['filename'])
    
    if not os.path.exists(file_path):
        abort(404)
    
    return send_from_directory(UPLOAD_FOLDER, file_info['filename'], as_attachment=True, download_name=file_info['name'])

@app.route('/api/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    # Check if token is valid
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"success": False, "message": "Token tidak valid"}), 401
    
    # In a real app, you would validate the token here
    # For simplicity, we'll skip token validation
    
    files_db = get_files_db()
    
    # Find file
    file_index = -1
    for i, file in enumerate(files_db):
        if file['id'] == file_id:
            file_index = i
            break
    
    if file_index == -1:
        return jsonify({"success": False, "message": "File tidak ditemukan"}), 404
    
    # Delete file from filesystem
    file_info = files_db[file_index]
    file_path = os.path.join(UPLOAD_FOLDER, file_info['filename'])
    
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Remove from database
    files_db.pop(file_index)
    save_files_db(files_db)
    
    return jsonify({
        "success": True,
        "message": "File berhasil dihapus"
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)