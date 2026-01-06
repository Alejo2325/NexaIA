from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests, os, json
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI
from datetime import datetime

app = FastAPI()

# 🔐 Configuración
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SHEET_ID = os.getenv("SHEET_ID")

client = OpenAI(api_key=OPENAI_API_KEY)

# 🧠 Prompt humano (asesor automotriz)
SYSTEM_PROMPT = """
Eres un asesor comercial de venta de carros y camiones.
Hablas natural, cercano y profesional.
Nunca dices que eres un bot o inteligencia artificial.
Haces preguntas cortas y humanas.
Tu objetivo es entender qué vehículo busca el cliente
y coordinar una llamada con un asesor humano.
"""

# 📄 Google Sheets
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(SHEET_ID).sheet1

# 🧠 Memoria simple por teléfono
memory = {}


# ✅ Verificación webhook
@app.get("/webhook")
def verify(request: Request):
    p = request.query_params
    if p.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(p.get("hub.challenge"))
    return PlainTextResponse("Error", status_code=403)


# 📩 Mensajes entrantes
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()

    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        text = msg["text"]["body"].strip().lower()
        phone = msg["from"]

        if phone not in memory:
            memory[phone] = {}

        # 🖐 Saludo natural
        if text in ["hola", "buenas", "buen día", "buenas tardes", "hey"]:
            send_message(phone, "Hola 😊 qué gusto saludarte. ¿Estás buscando un carro o un camión?")
            return "EVENT_RECEIVED"

        # Detectar tipo
        if "camión" in text or "camion" in text:
            memory[phone]["tipo"] = "Camión"
            send_message(phone, "Perfecto 👍 ¿Algún modelo o marca que tengas en mente?")
            return "EVENT_RECEIVED"

        if "carro" in text or "auto" in text:
            memory[phone]["tipo"] = "Carro"
            send_message(phone, "Excelente 😊 ¿Qué modelo o marca te interesa?")
            return "EVENT_RECEIVED"

        # Guardar vehículo de interés
        if "tipo" in memory[phone] and "vehiculo" not in memory[phone]:
            memory[phone]["vehiculo"] = text
            send_message(phone, "Muy bien. ¿Te gustaría que un asesor te llame para darte más información?")
            return "EVENT_RECEIVED"

        # Confirmar llamada
        if "sí" in text or "si" in text:
            send_message(phone, "Genial 🙌 ¿En qué horario te queda mejor la llamada?")
            return "EVENT_RECEIVED"

        # Guardar horario y cerrar lead
        if "mañana" in text or "tarde" in text or "hoy" in text:
            guardar_lead(
                fecha=datetime.now().strftime("%Y-%m-%d"),
                hora=text,
                nombre="Cliente WhatsApp",
                telefono=phone,
                tipo=memory[phone].get("tipo", ""),
                vehiculo=memory[phone].get("vehiculo", ""),
                comentarios="Solicita llamada"
            )
            send_message(phone, "Perfecto 😊 ya dejé todo registrado. Un asesor se comunicará contigo.")
            memory.pop(phone)
            return "EVENT_RECEIVED"

        # 💬 Conversación natural con IA
        respuesta = respuesta_humana(text)
        send_message(phone, respuesta)

    except Exception as e:
        print("Error:", e)

    return "EVENT_RECEIVED"


# 🧠 IA conversacional
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


# 📝 Guardar lead
def guardar_lead(fecha, hora, nombre, telefono, tipo, vehiculo, comentarios):
    sheet.append_row([
        fecha,
        hora,
        nombre,
        telefono,
        tipo,
        vehiculo,
        comentarios
    ])


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
