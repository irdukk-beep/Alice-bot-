import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# Ключ автоматически подтягивается из переменных окружения Vercel
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@app.route("/api/index", methods=["POST"])
def main():
  req = request.get_json(silent=True)

  # Обработка пустых запросов
  if not req or "request" not in req or "command" not in req["request"]:
    return jsonify({
        "version": "1.0",
        "response": {
            "text": "Бот успешно подключен и готов к работе!",
            "end_session": False,
        },
    })

  user_command = req["request"]["command"]

  # Первое приветствие при старте
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
  try:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # Используем сверхбыструю модель для голосовых помощников
    payload = {
        "model": "meta-llama/llama-3.2-3b-instruct:free",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Отвечай кратко, понятным языком, не более 2-3 предложений."
                ),
            },
            {"role": "user", "content": user_command},
        ],
        "max_tokens": 150,
    }

    # Короткий таймаут (2 секунды), чтобы уложиться в рамки Яндекса
    response = requests.post(
        OPENROUTER_URL, headers=headers, json=payload, timeout=2.0
    )

    if response.status_code == 200:
      data = response.json()
      ai_text = data["choices"][0]["message"]["content"]
    else:
      ai_text = "Нейросеть сейчас временно недоступна."

  except requests.exceptions.Timeout:
    ai_text = "Запрос обрабатывался слишком долго. Спросите покороче."
  except Exception:
    ai_text = "Произошла ошибка при обработке ответа."

  return jsonify({
      "version": req.get("version", "1.0"),
      "session": req.get("session", {}),
      "response": {"text": ai_text, "end_session": False},
  })


if __name__ == "__main__":
  app.run(debug=True)
