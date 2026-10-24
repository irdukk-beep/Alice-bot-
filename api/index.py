import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

PROVIDERS_CHAIN = [
    {
        "name": "Groq (Llama 8B)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": GROQ_API_KEY,
        "model": "llama-3.1-8b-instant",
        "timeout": 1.2,
        "headers": {"Content-Type": "application/json"},
    },
    {
        "name": "Groq (Llama 70B)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": GROQ_API_KEY,
        "model": "llama-3.3-70b-versatile",
        "timeout": 1.5,
        "headers": {"Content-Type": "application/json"},
    },
    {
        "name": "OpenRouter (DeepSeek)",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key": OPENROUTER_API_KEY,
        "model": "deepseek/deepseek-chat",
        "timeout": 2.2,
        "headers": {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://yandex.ru",
            "X-Title": "Alice Bot",
        },
    },
]


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

  ai_text = None
  error_logs = []

  for provider in PROVIDERS_CHAIN:
    key = provider["key"]
    if not key or not key.strip():
      error_logs.append(f"[{provider['name']}]: Ключ не задан в Vercel")
      continue

    try:
      headers = provider["headers"].copy()
      headers["Authorization"] = f"Bearer {key.strip()}"

      payload = {
          "model": provider["model"],
          "messages": [{"role": "user", "content": user_command}],
          "max_tokens": 40,
      }

      response = requests.post(
          provider["url"],
          headers=headers,
          json=payload,
          timeout=provider["timeout"],
      )

      if response.status_code == 200:
        data = response.json()
        ai_text = data["choices"][0]["message"]["content"]
        break
      else:
        err_msg = response.text[:80].replace("\n", " ")
        error_logs.append(
            f"[{provider['name']}] Код {response.status_code}: {err_msg}"
        )

    except requests.exceptions.Timeout:
      error_logs.append(
          f"[{provider['name']}]: Таймаут ({provider['timeout']}с)"
      )
    except Exception as e:
      error_logs.append(f"[{provider['name']}]: Ошибка {str(e)[:60]}")

  if not ai_text:
    ai_text = "Сбой всех нейросетей:\n" + "\n".join(error_logs)

  return jsonify({
      "version": req.get("version", "1.0"),
      "session": req.get("session", {}),
      "response": {"text": ai_text, "end_session": False},
  })


if __name__ == "__main__":
  app.run(debug=True)
