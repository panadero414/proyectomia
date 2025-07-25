
from flask import Flask, render_template, request, jsonify
import openai
import speech_recognition as sr
import random
import os
from fpdf import FPDF
from time import localtime, asctime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText 
from email.mime.application import MIMEApplication
from dotenv import load_dotenv


app = Flask(__name__)

# Configuración del servidor SMTP
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
load_dotenv()  #vars definidas en .env
openai.api_key = os.getenv("OPENAI_API_KEY")
SMTP_USERNAME   = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD   = os.getenv("SMTP_PASSWORD")

Edad = ""
Animal_favorito = ""
Nombre = ""
respuestas_usuario = []
respuestas_mia = []
preguntasHechasPorMIA = []

historial_txt = "Preguntas y respuestas.txt"
archivo_respuestas = open(historial_txt, "w", encoding="utf-8")

archivo_respuestas.write(asctime(localtime()) + "\n")
archivo_respuestas.write("BullyGuard MIA RELOADED\n\n")

def generar_pdf(nombre_txt, carpeta="reportes"):
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)
    with open(nombre_txt, "r", encoding="utf-8") as file:
        contenido = file.read()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, contenido)
    numero_reporte = 1
    while os.path.exists(f"{carpeta}/reporte_{numero_reporte}.pdf"):
        numero_reporte += 1
    nombre_pdf = f"{carpeta}/reporte_{numero_reporte}.pdf"
    pdf.output(nombre_pdf)
    return nombre_pdf

@app.route("/")
def index():
    global Nombre, Edad, Animal_favorito, lista_3_variables, pregunta_IA, Respuesta_IA, Pregunta_final_de_IA, pregunta_Quieres_agregar
    Nombre = ''
    Edad = ''
    Animal_favorito = ''
    lista_3_variables = []
    pregunta_IA = ''
    Respuesta_IA = ''
    Pregunta_final_de_IA = ''
    pregunta_Quieres_agregar = ''
    return render_template('index.html')

@app.route("/escuchar", methods=["POST"])
def escuchar():
    if os.getenv("FLASK_ENV") == "production":
        return jsonify({"mensaje": None})  # Evita usar micrófono en producción

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source)
            texto = recognizer.recognize_google(audio, language="es")
            return jsonify({"mensaje": texto})
        except Exception:
            return jsonify({"mensaje": None})


@app.route("/interactuar", methods=["POST"])
def interactuar():
    global Edad
    data = request.get_json()
    mensaje = data.get("mensaje", "")
    edad = Edad if Edad else "10"
    prompt = f"Soy un niño de {edad} años de edad me puedes contestar esta pregunta: {mensaje}, en un resumen máximo de 80 palabras respondeme de acuerdo a la edad del niño."

    try:
        respuesta = openai.ChatCompletion.create(
            model="gpt-4-0125-preview",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": mensaje}
            ],
            max_tokens=130
        )
        texto_respuesta = respuesta["choices"][0]["message"]["content"]
        archivo_respuestas.write(f"Niño: {mensaje}\nMIA: {texto_respuesta}\n\n")
        return jsonify({"respuesta": texto_respuesta})
    except Exception:
        return jsonify({"respuesta": "Hubo un problema al procesar la respuesta."})

@app.route('/reiniciar', methods=['POST'])
def reiniciar():
    with open("Preguntas y respuestas.txt", "w", encoding="utf-8") as f:
        f.write("")  # Limpia el archivo
    # Aquí también puedes reiniciar variables globales si hace falta
    return jsonify({"status": "ok"})


@app.route("/guardar_dato", methods=["POST"])
def guardar_dato():
    global Nombre, Edad, Animal_favorito
    data = request.get_json()
    tipo = data.get("tipo")
    valor = data.get("valor")
    if tipo == "nombre":
        Nombre = valor
    elif tipo == "edad":
        Edad = valor
    elif tipo == "animal":
        Animal_favorito = valor
    archivo_respuestas.write(f"{tipo.capitalize()}: {valor}\n")
    return jsonify({"estado": "ok"})

@app.route("/guardar_respuesta_mia", methods=["POST"])
def guardar_mia():
    global respuestas_mia
    data = request.get_json()
    respuesta = data.get("respuesta")
    respuestas_mia.append(respuesta)

    # Guardar en el archivo
    with open(historial_txt, "a", encoding="utf-8") as f:
        f.write(f"MIA: {respuesta}\n\n")

    return jsonify({"estado": "ok"})


@app.route("/guardar_respuesta_nino", methods=["POST"])
def guardar_nino():
    global respuestas_usuario
    data = request.get_json()
    respuesta = data.get("respuesta")
    respuestas_usuario.append(respuesta)

    # Guardar en el archivo
    with open(historial_txt, "a", encoding="utf-8") as f:
        f.write(f"Niño: {respuesta}\n")

    return jsonify({"estado": "ok"})

@app.route("/guardar_pregunta_mia", methods=["POST"])
def guardar_pregunta_mia():
    global preguntasHechasPorMIA
    data = request.get_json()
    pregunta = data.get("pregunta")
    preguntasHechasPorMIA.append(pregunta) 

    with open(historial_txt, "a", encoding="utf-8") as f:
        f.write(f"MIA pregunta: {pregunta}\n")
    
    return jsonify({"estado": "ok"})


@app.route("/analizar", methods=["POST"])
def analizar():
    global respuestas_usuario, respuestas_mia
    todo = respuestas_usuario + respuestas_mia

    try:
        respuesta_chiste = openai.ChatCompletion.create(
            model="gpt-4-0125-preview",
            messages=[
                {
                    "role": "system",
                    "content": f"Eres un psicólogo infantil especializado en bullying. Con un maximo de 100 palabras si detectas señales de bullying, da un consejo directo al niño. Si no, cuenta un chiste tierno (no menciones bullying). El niño tiene {Edad} años y le gusta {Animal_favorito}. Esto dijo: {todo}"
                },
                {"role": "user", "content": "Dame el consejo o el chiste según corresponda."}
            ],
            max_tokens=150
        )
        respuesta_visible = respuesta_chiste["choices"][0]["message"]["content"]

        respuesta_reporte = openai.ChatCompletion.create(
            model="gpt-4-0125-preview",
            messages=[
                {
                    "role": "system",
                    "content": f"Eres un psicólogo infantil que analiza si un niño sufre bullying. Con un maximo de 300 palabras basado en esto: {todo}"
                },
                {"role": "user", "content": "¿Este niño sufre bullying?"}
            ],
            max_tokens=400
        )
        resultado_analisis = respuesta_reporte["choices"][0]["message"]["content"]

        archivo_respuestas.write("\n*** Preguntas de MIA y respuestas del niño ***\n")
        for pregunta, respuesta in zip(preguntasHechasPorMIA, respuestas_mia):
            archivo_respuestas.write(f"MIA: {pregunta}\nNiño: {respuesta}\n\n")

        archivo_respuestas.write("*** Consejo o chiste ***\n")
        archivo_respuestas.write(respuesta_visible + "\n\n")
        archivo_respuestas.write("*** Análisis de bullying ***\n")
        archivo_respuestas.write(resultado_analisis + "\n\n")
        archivo_respuestas.write("Nota: El uso de esta tecnología no sustituye el diagnóstico y la atención de un profesional de la salud.\n")
        archivo_respuestas.close()
        generar_pdf(historial_txt)
        return jsonify({"resultado": respuesta_visible})
    except Exception as e:
        return jsonify({"resultado": "Hubo un problema en el análisis."})



@app.route('/enviar_reporte', methods=['POST'])
def enviar_reporte():
    data = request.get_json()
    email_destino = data.get('email')

    if not email_destino or '@' not in email_destino:
        return jsonify({'status': 'error', 'message': 'Correo inválido'})

    nombre_pdf = generar_pdf("Preguntas y respuestas.txt")

    mensaje = MIMEMultipart()
    mensaje['From'] = SMTP_USERNAME
    mensaje['To'] = email_destino
    mensaje['Subject'] = 'Reporte generado por MIA'

    cuerpo = MIMEText("Hola, adjunto encontrarás el reporte generado por MIA.\n\nAtentamente,\nMIA")
    mensaje.attach(cuerpo)

    with open(nombre_pdf, 'rb') as f:
        parte = MIMEApplication(f.read(), Name=os.path.basename(nombre_pdf))
        parte['Content-Disposition'] = f'attachment; filename="{os.path.basename(nombre_pdf)}"'
        mensaje.attach(parte)

    try:
        servidor = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        servidor.starttls()
        servidor.login(SMTP_USERNAME, SMTP_PASSWORD)
        servidor.send_message(mensaje)
        servidor.quit()
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
