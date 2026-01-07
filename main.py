from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests, os, json
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI
from datetime import datetime

app = FastAPI()

# =====================
# CONFIGURACIÓN
# =====================
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SHEET_ID = os.getenv("SHEET_ID")

client = OpenAI(api_key=OPENAI_API_KEY)

# =====================
# PROMPT HUMANO
# =====================
SYSTEM_PROMPT = """
Eres un asesor comercial de venta de carros y camiones.
Hablas de forma natural, cercana y profesional.
Nunca dices que eres un bot o inteligencia artificial.
Haces una sola pregunta a la vez.
Tu objetivo es entender qué vehículo busca el cliente
y coordinar una llamada con un asesor humano.
"""

# =====================
# GOOGLE SHEETS
# =====================
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(SHEET_ID).sheet1

# =====================
# MEMORIA SIMPLE
# =====================
memory = {}

# =====================
# WEBHOOK VERIFY
# =====================
@app.get("/webhook")
def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return PlainTextResponse(params.get("hub.challenge"))
    return PlainTextResponse("Error", status_code=403)

# =====================
# WEBHOOK MENSAJES
# =====================
@app.post("/webhook")
async def receive_message(request: Request):
    data = await request.json()
    print("DATA:", data)  # DEBUG

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        # Si no hay mensajes, salir
        if "messages" not in value:
            return "EVENT_RECEIVED"

        message = value["messages"][0]
        phone = message["from"]

        # Inicializar memoria
        if phone not in memory:
            memory[phone] = {}

        # Si no es texto
        if message.get("type") != "text":
            send_message(phone, "Hola 😊 ¿En qué te puedo ayudar?")
            return "EVENT_RECEIVED"

        text = message["text"]["body"].strip().lower()

        # =====================
        # SALUDO
        # =====================
        if text in ["hola", "buenas", "buen día", "buenos días", "buenas tardes", "hey"]:
            send_message(
                phone,
                "Hola 😊 qué gusto saludarte. ¿Estás buscando un carro o un camión?"
            )
            return "EVENT_RECEIVED"

        # =====================
        # TIPO DE VEHÍCULO
        # =====================
        if "camión" in text or "camion" in text:
            memory[phone]["tipo"] = "Camión"
            send_message(phone, "Perfecto 👍 ¿Algún modelo o marca que tengas en mente?")
            return "EVENT_RECEIVED"

        if "carro" in text or "auto" in text:
            memory[phone]["tipo"] = "Carro"
            send_message(phone, "Excelente 😊 ¿Qué modelo o marca te interesa?")
            return "EVENT_RECEIVED"

        # =====================
        # VEHÍCULO DE INTERÉS
        # =====================
        if "tipo" in memory[phone] and "vehiculo" not in memory[phone]:
            memory[phone]["vehiculo"] = text
            send_message(
                phone,
                "Muy bien. ¿Te gustaría que un asesor te llame para darte más información?"
            )
            return "EVENT_RECEIVED"

        # =====================
        # CONFIRMACIÓN LLAMADA
        # =====================
        if text in ["sí", "si", "claro", "de una", "ok", "vale"]:
            send_message(
                phone,
                "Genial 🙌 ¿En qué horario te queda mejor la llamada?"
            )
            return "EVENT_RECEIVED"

        # =====================
        # HORARIO → GUARDAR LEAD
        # =====================
        if any(palabra in text for palabra in ["mañana", "tarde", "hoy", "horario"]):
            guardar_lead(
                fecha=datetime.now().strftime("%Y-%m-%d"),
                hora=text,
                nombre="Cliente WhatsApp",
                telefono=phone,
                tipo=memory[phone].get("tipo", ""),
                vehiculo=memory[phone].get("vehiculo", ""),
                comentarios="Solicita llamada"
            )
            send_message(
                phone,
                "Perfecto 😊 ya dejé todo registrado. Un asesor se comunicará contigo."
            )
            memory.pop(phone)
            return "EVENT_RECEIVED"

        # =====================
        # IA CONVERSACIONAL
        # =====================
        respuesta = respuesta_humana(text)
        send_message(phone, respuesta)

    except Exception as e:
        print("ERROR:", e)

    return "EVENT_RECEIVED"

# =====================
# IA HUMANA
# =====================
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

# =====================
# GUARDAR LEAD
# =====================
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

# =====================
# ENVIAR WHATSAPP
# =====================
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
