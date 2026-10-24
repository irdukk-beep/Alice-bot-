from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

@app.route('/', methods=['POST'])
@app.route('/api/index', methods=['POST'])
def handler():
    req = request.get_json(force=True)
    user_text = req.get('request', {}).get('original_utterance', '')
    
    if not user_text:
        reply_text = "Привет! Я умный ассистент на базе DeepSeek. Чем могу помочь?"
    else:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek/deepseek-chat",
                    "messages": [{"role": "user", "content": user_text}]
                },
                timeout=8
            )
            data = response.json()
            reply_text = data['choices'][0]['message']['content']
        except Exception:
            reply_text = "Произошла ошибка при обращении к нейросети."

    return jsonify({
        "version": req.get("version", "1.0"),
        "session": req.get("session", {}),
        "response": {
            "text": reply_text[:1000],
            "end_session": False
        }
    })
