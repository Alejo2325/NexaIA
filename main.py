from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests
import os

app = FastAPI()

VERIFY_TOKEN = "nexa_verify_123"  # el mismo que pondrás en Meta
ACCESS_TOKEN = "EAAMRNbsWxJgBQeSkahYBRL8ldKb6jXenHu0JQuxPIPMZB5l3iE6DTXbPqapljIgJB7a4ZBq9FvYp54LV7V6CgWbvLkwqn3jI7e6vBbp2CbI4aa76Ix459uTkUTRhGnS1oUlZBqlVzZA1oFvZBGf4iZBzG8fFBBL2OEDXHLB8KfX9eZAwChpbcYXTVrAlJGEnWeb3gIL2BK9uHEKynq2EWZAVKEN9uZBjH4LeEpZA2kbTIjOt6QQ3QlsT8UueYxqVmRuZCt0lXuSZC5AaiK2jm4kKouVZA2QZDZD"
PHONE_NUMBER_ID = "956562447538656"

# 1️⃣ Verificación del webhook
@app.get("/webhook")
def verify(request: Request):
    params = request.query_params

    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return PlainTextResponse(params.get("hub.challenge"))

    return PlainTextResponse("Error de verificación", status_code=403)


@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]
        text = message["text"]["body"].lower().strip()

        if text in ["menu", "menú"]:
            send_message(from_number, MENU_TEXT)

        else:
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

MENU_TEXT = """
🍔 *MENÚ - Nexa Burger*

1. Hamburguesa Clásica — $12.000
2. Hamburguesa Doble — $16.000
3. Perro Caliente — $10.000
4. Papas a la francesa — $6.000
5. Gaseosa — $4.000

📦 Escribe el número del producto para pedir
"""
