import json
import os
from datetime import datetime
from google import genai
from google.genai import types
import streamlit as st

# Configuración del cliente con la clave guardada en los secretos del servidor
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
client = genai.Client(api_key=api_key)

# Prompt socrático del tutor de laboratorio
SYSTEM_INSTRUCTION = """
Eres "TutorFARO", un tutor académico especializado en guiar a estudiantes 
de asignaturas experimentales en la preparación de sus guiones de laboratorio.

REGLAS:
- Método Socrático: No des soluciones o fórmulas de forma directa. Haz preguntas para que el alumno razone.
- Pide siempre al estudiante que explique qué ha intentado o comprendido del guion.
- Mantén respuestas breves, estructuradas y empáticas.
"""


# Función para guardar las consultas de forma anónima
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
        except:
            datos = []
    datos.append(registro)
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


# Configuración de la interfaz en Streamlit
st.set_page_config(page_title="TutorFARO", page_icon="🔬")
st.title("🔬 Tutor de Prácticas de Laboratorio")
st.write(
    "Resuelve tus dudas sobre los guiones antes de la sesión presencial."
)

# Inicializar la conversación
if "chat" not in st.session_state:
    st.session_state.chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION, temperature=0.3
        ),
    )
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial en pantalla
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Entrada del estudiante
if prompt := st.chat_input("Escribe aquí tu duda sobre el guion..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    guardar_registro("estudiante", prompt)

    # Respuesta de la IA
    response = st.session_state.chat.send_message(prompt)

    st.session_state.messages.append(
        {"role": "assistant", "content": response.text}
    )
    with st.chat_message("assistant"):
        st.markdown(response.text)

    guardar_registro("tutor", response.text)
# Botón para descargar el registro de interacciones
if os.path.exists("registro_dudas.json"):
    with open("registro_dudas.json", "r", encoding="utf-8") as f:
        datos_json = f.read()

    st.download_button(
        label="📥 Descargar registros (JSON)",
        data=datos_json,
        file_name="registro_dudas.json",
        mime="application/json",
    )
