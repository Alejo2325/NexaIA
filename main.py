from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests
import os

app = FastAPI()

VERIFY_TOKEN = "nexa_verify_123"  # el mismo que pondrás en Meta
ACCESS_TOKEN = "EAAMRNbsWxJgBQYP6g05cw7QqyPjzfXzia8lLASbTL0LloD1eBQOnKPK3YGjAx7r9SBNz4zPU5hI8eIrRm9TGFfebuRKXPCVatuT5zQp6BGMKUrP24PAtu6o5FbzK4ZAO4wg129AydZBZCCpA66Fc0bFj1e8FYc1jO2jJ7DZCro2euFbw9CMSePwJgTWIs0LVuil8pzcb0gsfmOzF4vkGjkW1xE2NLTCPOR9HPfnCugdI985zU21ATe3cAMiEqPJ5Vo4hZBBYWxZAnZCxvSpsFUmbQZDZDEAAMRNbsWxJgBQdzuzN4Kj5yQlAOan7gbTxwL0DVdgGZAJRrfEvmgQLS9jHMQVWNYj5y7zCO0bisEYZCoFw10aMDhAIqrEvRWe3zCTrVZCwmXgkYWWnWs1RLp4HdylitZBmZAixixNCaEStOxZAoBKZA8isNUKLPQ1VYwTIavOc8qTlSq2MkDbFNd0xHkh39dZBsBK7SVZBVXDhQeNSbxgztHPs0bwrIOqz3fk3NZAhzdgXl2Wx3KOK8MZAuRVE0PyFPwQlnZALouhJV3WeBJI6BfelXB"
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

# 2️⃣ Recepción de mensajes
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]
        text = message["text"]["body"]

        send_message(from_number, f"🍔 Hola! Gracias por escribir a Nexa IA.\n\nDime *MENÚ* para ver nuestros platos.")

    except Exception as e:
        print("Error:", e)

    return "EVENT_RECEIVED"

# 3️⃣ Enviar mensaje por WhatsApp
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
