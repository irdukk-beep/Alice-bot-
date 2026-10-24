import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@app.route("/api/index", methods=["POST"])
def main():
  # Безопасно получаем JSON от Яндекс Диалогов
  req = request.get_json(silent=True)

  # Защита от пустых запросов или тестов от Яндекса
  if not req or "request" not in req or "command" not in req["request"]:
    return jsonify({
        "version": "1.0",
        "response": {
            "text": "Бот успешно подключен и готов к работе!",
            "end_session": False,
        },
    })

  user_command = req["request"]["command"]

  # Если пользователь просто запустил навык без текста
  if not user_command.strip():
    return jsonify({
        "version": req.get("version", "1.0"),
        "session": req.get("session", {}),
        "response": {
            "text": "Привет! Я на связи. Что бы вы хотели обсудить?",
            "end_session": False,
        },
    })

  ai_text = "Извините, не удалось получить ответ от нейросети."
  try:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yandex.ru",
        "X-Title": "Alice DeepSeek Bot",
    }

    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": user_command}],
        "max_tokens": 300,
    }

    # Таймаут 2.5 секунды, чтобы Яндекс не успел выдать ошибку
    response = requests.post(
        OPENROUTER_URL, headers=headers, json=payload, timeout=2.5
    )

    if response.status_code == 200:
      data = response.json()
      ai_text = data["choices"][0]["message"]["content"]
    else:
      ai_text = "Ошибка обращения к нейросети. Попробуйте позже."

  except requests.exceptions.Timeout:
    ai_text = "Нейросеть отвечает слишком долго. Попробуйте сформулировать запрос короче."
  except Exception as e:
    ai_text = "Произошла системная ошибка на сервере."

  return jsonify({
      "version": req.get("version", "1.0"),
      "session": req.get("session", {}),
      "response": {"text": ai_text, "end_session": False},
  })


if __name__ == "__main__":
  app.run(debug=True)
