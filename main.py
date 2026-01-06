from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests, os, json
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI

app = FastAPI()

# 🔐 Config
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SHEET_ID = os.getenv("SHEET_ID")

client = OpenAI(api_key=OPENAI_API_KEY)

# 🧠 Prompt humano
SYSTEM_PROMPT = """
Eres una persona real atendiendo WhatsApp de un negocio.
Hablas natural, cercano y amable.
Nunca usas listas ni números.
Nunca dices que eres un bot o inteligencia artificial.
Tu objetivo es ayudar y, si el cliente quiere, agendar una cita.
Respondes como una persona normal.
"""

# 📄 Google Sheets
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(SHEET_ID).sheet1


# ✅ Verificación webhook
@app.get("/webhook")
def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(params.get("hub.challenge"))
    return PlainTextResponse("Error", status_code=403)


# 📩 Mensajes entrantes
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()

    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        text = msg["text"]["body"].strip().lower()
        phone = msg["from"]

        # 🖐 Saludo natural
        if text in ["hola", "buenas", "buen día", "buenas tardes", "hey"]:
            send_message(phone, "Hola 😊 qué gusto saludarte. ¿En qué te puedo ayudar?")
            return "EVENT_RECEIVED"

        # 📅 Intención de cita
        if "cita" in text or "agendar" in text or "reservar" in text:
            send_message(phone, "Perfecto 🙌 dime para qué servicio y qué día te gustaría.")
            return "EVENT_RECEIVED"

        # 📝 Detectar datos básicos (simple)
        if any(word in text for word in ["mañana", "hoy", "lunes", "martes", "miércoles", "jueves", "viernes"]):
            guardar_cita(
                fecha="Por confirmar",
                hora="Por confirmar",
                nombre="Cliente WhatsApp",
                servicio=text,
                telefono=phone
            )
            send_message(phone, "Listo 😊 ya tomé nota de tu cita. En un momento te confirmo.")
            return "EVENT_RECEIVED"

        # 💬 Conversación natural (IA)
        respuesta = respuesta_humana(text)
        send_message(phone, respuesta)

    except Exception as e:
        print("Error:", e)

    return "EVENT_RECEIVED"


# 🧠 Respuesta humana
def respuesta_humana(mensaje):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": mensaje}
        ],
        temperature=0.7,
        max_tokens=120
    )
    return response.choices[0].message.content.strip()


# 📝 Guardar cita
def guardar_cita(fecha, hora, nombre, servicio, telefono):
    sheet.append_row([fecha, hora, nombre, servicio, telefono])


# 📤 Enviar WhatsApp
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
