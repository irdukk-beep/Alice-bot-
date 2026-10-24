import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "ВАШ_КЛЮЧ")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


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

  ai_text = "Ошибка обработки."
  try:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yandex.ru",
        "X-Title": "Alice Bot",
    }

    payload = {
        "model": "meta-llama/llama-3.2-3b-instruct:free",
        "messages": [{"role": "user", "content": user_command}],
        "max_tokens": 150,
    }

    response = requests.post(
        OPENROUTER_URL, headers=headers, json=payload, timeout=2.5
    )

    if response.status_code == 200:
      data = response.json()
      ai_text = data["choices"][0]["message"]["content"]
    else:
      # Выводим точный код и текст ошибки от OpenRouter в чат для проверки
      ai_text = (
          f"Ошибка API ({response.status_code}): {response.text[:120]}"
      )

  except requests.exceptions.Timeout:
    ai_text = "Превышен таймаут ожидания нейросети."
  except Exception as e:
    ai_text = f"Системная ошибка: {str(e)[:50]}"

  return jsonify({
      "version": req.get("version", "1.0"),
      "session": req.get("session", {}),
      "response": {"text": ai_text, "end_session": False},
  })


if __name__ == "__main__":
  app.run(debug=True)
