import os
import re
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

SYSTEM_PROMPT = (
    "Ты — умный голосовой ассистент, работающий через навык Яндекс Алисы. "
    "Если тебя спрашивают, кто ты или на какой нейросети ты работаешь, "
    "объясняй, что ты независимая языковая модель (искусственный интеллект), "
    "подключенная к этому навыку. Никогда не притворяйся официальной инфраструктурой Яндекса. "
    "Отвечай на том языке, на котором к тебе обратился пользователь. "
    "Ответы должны быть краткими, живыми и понятными на слух. "
    "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО: использовать ссылки, URL-адреса, списки с квадратными скобками, "
    "Markdown-разметку, звездочки и решетки."
)

PROVIDERS_CHAIN = [
    {
        "name": "Groq (Llama 8B)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": GROQ_API_KEY,
        "model": "llama-3.1-8b-instant",
        "timeout": 1.0,
        "headers": {"Content-Type": "application/json"},
    },
    {
        "name": "Groq (Llama 70B)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": GROQ_API_KEY,
        "model": "llama-3.3-70b-versatile",
        "timeout": 1.2,
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

# Хранилище истории диалогов в памяти
# Формат: {session_id: [{"role": "user"/"assistant", "content": "..."}]}
sessions_history = {}


def clean_text_for_alice(text: str) -> str:
  text = re.sub(r"[\*#_`~\[\]\\]", "", text)
  return text.strip()


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

  session_data = req.get("session", {})
  session_id = session_data.get("session_id", "default")
  is_new_session = session_data.get("new", False)

  # Сбрасываем историю, если началась новая сессия
  if is_new_session or session_id not in sessions_history:
    sessions_history[session_id] = []

  user_command = req["request"]["command"]

  if not user_command.strip():
    return jsonify({
        "version": req.get("version", "1.0"),
        "session": session_data,
        "response": {
            "text": "Привет! Я на связи. Что бы вы хотели обсудить?",
            "end_session": False,
        },
    })

  # Добавляем сообщение пользователя в историю текущей сессии
  sessions_history[session_id].append(
      {"role": "user", "content": user_command}
  )

  # Ограничиваем контекст последними 6 сообщениями (3 шага диалога) для экономии лимитов
  recent_history = sessions_history[session_id][-6:]

  # Формируем полный набор сообщений с системным промптом
  messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
  messages_payload.extend(recent_history)

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
          "messages": messages_payload,
          "max_tokens": 100,
      }

      response = requests.post(
          provider["url"],
          headers=headers,
          json=payload,
          timeout=provider["timeout"],
      )

      if response.status_code == 200:
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]
        ai_text = clean_text_for_alice(raw_content)

        # Сохраняем ответ ассистента в историю
        sessions_history[session_id].append(
            {"role": "assistant", "content": ai_text}
        )
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
    # Удаляем последнее сообщение пользователя, если ответ не был получен
    if sessions_history[session_id]:
      sessions_history[session_id].pop()
    ai_text = "Сбой всех нейросетей:\n" + "\n".join(error_logs)

  return jsonify({
      "version": req.get("version", "1.0"),
      "session": session_data,
      "response": {"text": ai_text, "end_session": False},
  })


if __name__ == "__main__":
  app.run(debug=True)
