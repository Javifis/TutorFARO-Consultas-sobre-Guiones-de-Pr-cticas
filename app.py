import json
import os
from datetime import datetime
from google import genai
from google.genai import types
import streamlit as st

# 1. Configuración de página
st.set_page_config(page_title="TutorFARO", page_icon="🔬")

# 2. Validación y obtención de API Key
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error(
        "⚠️ Falta la clave API. Ve a Settings > Secrets en Streamlit Cloud e introduce GEMINI_API_KEY."
    )
    st.stop()

# 3. Inicializar el cliente en CADA ejecución para evitar que se cierre la conexión HTTP
client = genai.Client(api_key=api_key)

# 4. Prompt socrático del tutor
SYSTEM_INSTRUCTION = """
Eres "TutorFARO", un tutor académico especializado en guiar a estudiantes 
de asignaturas experimentales en la preparación de sus guiones de laboratorio.

REGLAS:
- Método Socrático: No des soluciones o fórmulas de forma directa. Haz preguntas para que el alumno razone.
- Pide siempre al estudiante que explique qué ha intentado o comprendido del guion.
- Mantén respuestas breves, estructuradas y empáticas.
"""


# 5. Función de guardado de registros
def guardar_registro(rol, texto):
    registro = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rol": rol,
        "mensaje": texto,
    }
    archivo = "registro_dudas.json"
    datos = []
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)
        except Exception:
            datos = []
    datos.append(registro)
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


# 6. Interfaz principal
st.title("🔬 Tutor de Prácticas de Laboratorio")
st.write("Resuelve tus dudas sobre los guiones antes de la sesión presencial.")

# Inicializar historial de mensajes en la sesión
if "messages" not in st.session_state:
    st.session_state.messages = []

# Inicializar o reconectar el chat con el cliente activo
if "chat" not in st.session_state:
    st.session_state.chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
        ),
    )
else:
    # Reasignar el cliente activo a la sesión existente para evitar el error 'client has been closed'
    st.session_state.chat._api_client = client._api_client

# Mostrar mensajes anteriores
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Entrada de texto del alumno
if prompt := st.chat_input("Escribe aquí tu duda sobre el guion..."):
    # Mostrar y registrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    guardar_registro("estudiante", prompt)

    # Generar respuesta con manejo de errores
    try:
        response = st.session_state.chat.send_message(prompt)
        respuesta_texto = response.text
    except Exception:
        # Si la sesión antigua caducó por completo, recrea el chat y reintenta
        st.session_state.chat = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.3,
            ),
        )
        response = st.session_state.chat.send_message(prompt)
        respuesta_texto = response.text

    # Mostrar y registrar respuesta del tutor
    st.session_state.messages.append(
        {"role": "assistant", "content": respuesta_texto}
    )
    with st.chat_message("assistant"):
        st.markdown(respuesta_texto)

    guardar_registro("tutor", respuesta_texto)

# Botón para descargar registros al final de la página
if os.path.exists("registro_dudas.json"):
    with open("registro_dudas.json", "r", encoding="utf-8") as f:
        datos_json = f.read()

    st.download_button(
        label="📥 Descargar registros (JSON)",
        data=datos_json,
        file_name="registro_dudas.json",
        mime="application/json",
    )
