from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
from urllib.parse import urlparse
import logging

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
allowedOrigins = os.getenv(
    'CORS_ORIGINS',
    'https://zoomish.github.io,https://aryzhkova2112-rgb.github.io,http://localhost:5500,http://127.0.0.1:5500'
).split(',')
CORS(app, origins=[origin.strip() for origin in allowedOrigins if origin.strip()])


# ============================================
# ПОДКЛЮЧЕНИЕ К POSTGRESQL ЧЕРЕЗ
# ============================================
def get_db_connection():
    databaseUrl = os.getenv('DATABASE_URL')
    if databaseUrl:
        parsed = urlparse(databaseUrl)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/'),
            sslmode='require'
        )

    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'admin'),
        database=os.getenv('DB_NAME', 'beauty_salon')
    )

# ============================================
# СТАТИЧЕСКИЕ ФАЙЛЫ (относительные пути)
# ============================================
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    # Безопасная отдача статических файлов
    # Запрещаем доступ к системным файлам
    dangerous_patterns = ['..', '~', '.env', '.git', '__pycache__']
    for pattern in dangerous_patterns:
        if pattern in filename:
            return "Forbidden", 403
    return send_from_directory('.', filename)


# ============================================
# 1. АВТОРИЗАЦИЯ
# ============================================
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (data['username'], data['password'])
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            return jsonify({
                "success": True,
                "role": user['role'],
                "name": user['name'],
                "user_id": user['id']
            })
        return jsonify({"success": False}), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# 2. ПОЛУЧЕНИЕ УСЛУГ
# ============================================
@app.route('/api/services', methods=['GET'])
def get_services():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT * FROM services")
        services = cursor.fetchall()
        cursor.close()
        conn.close()
        result = [dict(service) for service in services]
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_services: {e}")
        return jsonify([]), 500


# ============================================
# 3. ОБНОВЛЕНИЕ ЦЕНЫ
# ============================================
@app.route('/api/services/<int:id>', methods=['PATCH'])
def update_price(id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE services SET price = %s WHERE id = %s",
            (data['price'], id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error in update_price: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# 4. ПОЛУЧЕНИЕ ПОРТФОЛИО
# ============================================
@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT id, image_url, title FROM portfolio ORDER BY id")
        photos = cursor.fetchall()
        cursor.close()
        conn.close()
        result = [dict(photo) for photo in photos]
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_portfolio: {e}")
        return jsonify([]), 500


# ============================================
# 5. ДОБАВЛЕНИЕ ФОТО
# ============================================
@app.route('/api/portfolio', methods=['POST'])
def add_photo():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO portfolio (image_url, title, created_by) VALUES (%s, %s, %s)",
            (data['image_url'], data.get('title', ''), data.get('user_id', 1))
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error in add_photo: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# 6. УДАЛЕНИЕ ФОТО
# ============================================
@app.route('/api/portfolio/<int:id>', methods=['DELETE'])
def delete_photo(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM portfolio WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error in delete_photo: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# 7. ПОЛУЧЕНИЕ ВИДЕО
# ============================================
@app.route('/api/videos', methods=['GET'])
def get_videos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT * FROM videos")
        videos = cursor.fetchall()
        cursor.close()
        conn.close()
        result = [dict(video) for video in videos]
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_videos: {e}")
        return jsonify([]), 500


# ============================================
# 8. ДОБАВЛЕНИЕ ВИДЕО
# ============================================
@app.route('/api/videos', methods=['POST'])
def add_video():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO videos (video_url, title, created_by) VALUES (%s, %s, %s)",
            (data['video_url'], data.get('title', ''), data.get('user_id', 1))
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error in add_video: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# 9. УДАЛЕНИЕ ВИДЕО
# ============================================
@app.route('/api/videos/<int:id>', methods=['DELETE'])
def delete_video(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM videos WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error in delete_video: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# 10. ПОЛУЧЕНИЕ ЦЕН НА ВЫЕЗД
# ============================================
@app.route('/api/visit-prices', methods=['GET'])
def get_visit_prices():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT * FROM visit_prices")
        prices = cursor.fetchall()
        cursor.close()
        conn.close()
        result = [dict(price) for price in prices]
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_visit_prices: {e}")
        return jsonify([]), 500


# ============================================
# 11. ОБНОВЛЕНИЕ ЦЕН НА ВЫЕЗД
# ============================================
@app.route('/api/visit-prices/<int:id>', methods=['PATCH'])
def update_visit_price(id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE visit_prices SET price = %s WHERE id = %s",
            (data['price'], id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error in update_visit_price: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================
if __name__ == '__main__':
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'

    logger.info(f"Starting server on {host}:{port}, debug={debug}")
    app.run(debug=debug, host=host, port=port)