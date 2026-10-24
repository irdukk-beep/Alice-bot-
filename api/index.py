import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# Ключ подтягивается автоматически из настроек Vercel для Groq
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Список моделей по порядку приоритета (основная и запасная)
MODELS_CHAIN = ["llama-3.1-8b-instant", "gemma2-9b-it"]


@app.route("/api/index", methods=["POST"])
def main():
  req = request.get_json(silent=True)

  if not req or "request" not in req or "command" not in req["request"]:
    return jsonify({
        "version": "1.0",
        "response": {
            "text": "Бот успешно подключен и готов к работе!",
            "end_session": False,
        },
    })

  user_command = req["request"]["command"]

  if not user_command.strip():
    return jsonify({
        "version": req.get("version", "1.0"),
        "session": req.get("session", {}),
        "response": {
            "text": "Привет! Я на связи. Что бы вы хотели обсудить?",
            "end_session": False,
        },
    })

  ai_text = "Извините, не удалось получить ответ."
  headers = {
      "Authorization": f"Bearer {GROQ_API_KEY}",
      "Content-Type": "application/json",
  }

  # Проходим по цепочке моделей: если первая не ответила вовремя, пробуем вторую
  for model_name in MODELS_CHAIN:
    try:
      payload = {
          "model": model_name,
          "messages": [{"role": "user", "content": user_command}],
          "max_tokens": 50,  # Короткий ответ для мгновенной генерации
      }

      # Выделяем на каждую попытку по 1.3 секунды
      response = requests.post(
          GROQ_URL, headers=headers, json=payload, timeout=1.3
      )

      if response.status_code == 200:
        data = response.json()
        ai_text = data["choices"][0]["message"]["content"]
        break  # Успешно получили ответ — прерываем цикл
    except Exception:
      continue  # Если возникла ошибка или таймаут, цикл перейдет к следующей модели

  return jsonify({
      "version": req.get("version", "1.0"),
      "session": req.get("session", {}),
      "response": {"text": ai_text, "end_session": False},
  })


if __name__ == "__main__":
  app.run(debug=True)
