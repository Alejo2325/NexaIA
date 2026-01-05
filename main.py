from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests
import os

app = FastAPI()

VERIFY_TOKEN = "nexa_verify_123"  # el mismo que pondrás en Meta
ACCESS_TOKEN = "EAAMRNbsWxJgBQeSkahYBRL8ldKb6jXenHu0JQuxPIPMZB5l3iE6DTXbPqapljIgJB7a4ZBq9FvYp54LV7V6CgWbvLkwqn3jI7e6vBbp2CbI4aa76Ix459uTkUTRhGnS1oUlZBqlVzZA1oFvZBGf4iZBzG8fFBBL2OEDXHLB8KfX9eZAwChpbcYXTVrAlJGEnWeb3gIL2BK9uHEKynq2EWZAVKEN9uZBjH4LeEpZA2kbTIjOt6QQ3QlsT8UueYxqVmRuZCt0lXuSZC5AaiK2jm4kKouVZA2QZDZD"
PHONE_NUMBER_ID = "956562447538656"
SYSTEM_PROMPT = """
Eres un asistente virtual de un restaurante de comida rápida.
Respondes corto, amable y claro.
Nunca hablas de tecnología ni IA.
Siempre intentas llevar al cliente a pedir del menú.
"""


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
        text = message["text"]["body"].strip().lower()

        # MENÚ
        if text in ["menu", "menú"]:
            send_message(from_number, MENU_TEXT)
            return "EVENT_RECEIVED"

        # OPCIÓN VÁLIDA
        if text.isdigit():
            if text in PRODUCTS:
                product, price = PRODUCTS[text]
                send_message(
                    from_number,
                    f"✅ *Pedido recibido*\n\n"
                    f"🍽 Producto: {product}\n"
                    f"💰 Precio: ${price:,}\n\n"
                    f"📍 Escribe tu *dirección* o escribe *RECOGER*"
                )
            else:
                send_message(
                    from_number,
                    "❌ *Opción no disponible*\n\n"
                    "👉 Escribe *MENU* para ver las opciones válidas 🍔"
                )
            return "EVENT_RECEIVED"

        # RECOGER
        if text == "recoger":
            send_message(
                from_number,
                "🕒 Tu pedido estará listo en 20 minutos.\n"
                "📍 Dirección: Calle 123 #45-67\n\n"
                "¡Gracias por tu pedido! 🙌"
            )
            return "EVENT_RECEIVED"

        # DIRECCIÓN (delivery)
        if len(text) > 8:
            send_message(
                from_number,
                "🚴 *Pedido en camino*\n\n"
                "⏱ Tiempo estimado: 30 minutos\n\n"
                "¡Gracias por pedir con Nexa IA! 🍔"
            )
            return "EVENT_RECEIVED"

        # BIENVENIDA
        ai_response = ai_reply(text)
        send_message(from_number, ai_response)     

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

def ai_reply(user_text):
    if "recomiendas" in user_text:
        return "🍔 Te recomiendo la *Hamburguesa Doble*, es la favorita 😋\nEscribe *MENU* para pedir."
    if "económico" in user_text:
        return "💰 El producto más económico es el *Perro Caliente* por $10.000"
    if "demoran" in user_text or "tiempo" in user_text:
        return "⏱ El tiempo promedio es de 20 a 30 minutos."
    return "🤔 Escríbeme *MENU* para ver las opciones disponibles 🍔"


PRODUCTS = {
    "1": ("Hamburguesa Clásica", 12000),
    "2": ("Hamburguesa Doble", 16000),
    "3": ("Perro Caliente", 10000),
    "4": ("Papas a la francesa", 6000),
    "5": ("Gaseosa", 4000),
}

MENU_TEXT = """
🍔 *MENÚ - Nexa Burger*

1️⃣ Hamburguesa Clásica — $12.000
2️⃣ Hamburguesa Doble — $16.000
3️⃣ Perro Caliente — $10.000
4️⃣ Papas a la francesa — $6.000
5️⃣ Gaseosa — $4.000

📦 Escribe el número del producto para pedir
"""


WELCOME_TEXT = (
    "👋 *Bienvenido a Nexa Burger*\n\n"
    "🍔 Pide sin esperar en WhatsApp\n\n"
    "👉 Escribe *MENU* para ver nuestros platos"
)
