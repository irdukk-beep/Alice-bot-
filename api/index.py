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

# Оптимизированная цепочка с короткими тайм-аутами (суммарно строго до 2.5 сек)
PROVIDERS_CHAIN = [
    {
        "name": "Groq (Llama 8B)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": GROQ_API_KEY,
        "model": "llama-3.1-8b-instant",
        "timeout": 0.8,
        "headers": {"Content-Type": "application/json"},
    },
    {
        "name": "Groq (Llama 70B)",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": GROQ_API_KEY,
        "model": "llama-3.3-70b-versatile",
        "timeout": 1.0,
        "headers": {"Content-Type": "application/json"},
    },
    {
        "name": "OpenRouter (DeepSeek)",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key": OPENROUTER_API_KEY,
        "model": "deepseek/deepseek-chat",
        "timeout": 1.5,
        "headers": {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://yandex.ru",
            "X-Title": "Alice Bot",
        },
    },
]


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

    for provider in PROVIDERS_CHAIN:
        key = provider["key"]
        if not key or not key.strip():
            continue

        try:
            headers = provider["headers"].copy()
            headers["Authorization"] = f"Bearer {key.strip()}"

            payload = {
                "model": provider["model"],
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_command},
                ],
                "max_tokens": 80,
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
                break
        except Exception:
            continue

    # Если абсолютно все провайдеры упали или не успели, возвращаем мягкую заглушку,
    # чтобы Яндекс не выдавал ошибку тайм-аута, а озвучил понятный текст.
    if not ai_text:
        ai_text = "Извините, сервис перегружен, попробуйте еще раз."

    return jsonify({
        "version": req.get("version", "1.0"),
        "session": req.get("session", {}),
        "response": {"text": ai_text, "end_session": False},
    })


if __name__ == "__main__":
    app.run(debug=True)
