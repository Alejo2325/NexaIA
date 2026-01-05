from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests

app = FastAPI()

VERIFY_TOKEN = "nexa_verify_123"
ACCESS_TOKEN = "TU_TOKEN_AQUI"
PHONE_NUMBER_ID = "956562447538656"


# ✅ VERIFICACIÓN CORRECTA PARA META
@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)

    return PlainTextResponse("Forbidden", status_code=403)


# 📩 RECEPCIÓN DE MENSAJES
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]

        send_message(
            from_number,
            "🍔 Hola! Gracias por escribir a Nexa IA.\n\nEscribe *MENU* para ver nuestros platos."
        )

    except Exception as e:
        print("Error:", e)

    return "EVENT_RECEIVED"


def send_message(to, body):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body}
    }
    requests.post(url, headers=headers, json=payload)
