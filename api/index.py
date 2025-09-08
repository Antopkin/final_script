import requests
import json
import os
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta

# --- ГЛАВНАЯ ФУНКЦИЯ-ОБРАБОТЧИК ---
# Она будет принимать все запросы, которые приходят на ваш URL

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        # Получаем тело запроса
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            body = json.loads(post_data)
            action_type = body.get('action_type')
            params = body.get('params')
            
            # Вызываем нашу логику Wordstat
            result = handle_wordstat_request(action_type, params)
            
            # Отправляем успешный ответ
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            # Отправляем ответ с ошибкой
            error_response = {"status": "error", "message": str(e)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
            
        return

# --- ЛОГИКА РАБОТЫ С WORDSTAT API (из прошлого шага) ---

def handle_wordstat_request(action_type: str, params: dict):
    TOKEN = os.getenv('YANDEX_TOKEN')
    API_BASE_URL = 'https://api.wordstat.yandex.net/v1'
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    if not TOKEN:
        return {"status": "error", "message": "YANDEX_TOKEN is not configured on the server."}

    keyword = params.get('keyword')
    if not keyword:
        return {"status": "error", "message": "Parameter 'keyword' is required."}

    # Определяем, какую функцию вызвать
    if action_type == 'seo_keywords':
        num_keywords = params.get('num_keywords', 20)
        return find_seo_keywords(keyword, num_keywords, headers, API_BASE_URL)
    elif action_type == 'seasonality':
        return analyze_seasonality(keyword, headers, API_BASE_URL)
    else:
        return {"status": "error", "message": f"Unknown action_type: {action_type}"}

# --- Функции для конкретных запросов к API ---

def find_seo_keywords(main_keyword, num_keywords, headers, base_url):
    """Поиск связанных ключевых слов для SEO."""
    try:
        response = requests.post(
            f"{base_url}/topRequests",
            headers=headers,
            json={"phrase": main_keyword, "numPhrases": num_keywords, "regions": [225]}
        )
        response.raise_for_status()
        data = response.json()
        keywords = [{'keyword': r.get('phrase'), 'searches': r.get('count')} for r in data.get('topRequests', [])]
        return {"status": "success", "data": keywords}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": "API request failed", "details": e.response.text if e.response else "No response"}

def analyze_seasonality(keyword, headers, base_url):
    """Анализ сезонности запроса."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    try:
        response = requests.post(
            f"{base_url}/dynamics",
            headers=headers,
            json={
                "phrase": keyword, "period": "month",
                "fromDate": start_date.strftime("%Y-%m-%d"), "toDate": end_date.strftime("%Y-%m-%d"),
                "regions": [225]
            }
        )
        response.raise_for_status()
        return {"status": "success", "data": response.json().get('dynamics', [])}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": "API request failed", "details": e.response.text if e.response else "No response"}