import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

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

  if not GROQ_API_KEY:
    return jsonify({
        "version": req.get("version", "1.0"),
        "session": req.get("session", {}),
        "response": {
            "text": "Ошибка: Ключ GROQ_API_KEY не найден в Vercel!",
            "end_session": False,
        },
    })

  ai_text = None
  last_error = ""

  headers = {
      "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
      "Content-Type": "application/json",
  }

  for model_name in MODELS_CHAIN:
    try:
      payload = {
          "model": model_name,
          "messages": [{"role": "user", "content": user_command}],
          "max_tokens": 50,
      }

      response = requests.post(
          GROQ_URL, headers=headers, json=payload, timeout=2.0
      )

      if response.status_code == 200:
        data = response.json()
        ai_text = data["choices"][0]["message"]["content"]
        break
      else:
        last_error = (
            f"[{model_name}] Err {response.status_code}: {response.text[:100]}"
        )
    except Exception as e:
      last_error = f"[{model_name}] Ex: {str(e)[:80]}"

  if not ai_text:
    ai_text = f"Ошибка Groq: {last_error}"

  return jsonify({
      "version": req.get("version", "1.0"),
      "session": req.get("session", {}),
      "response": {"text": ai_text, "end_session": False},
  })


if __name__ == "__main__":
  app.run(debug=True)
