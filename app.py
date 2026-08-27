import json
import os
from datetime import datetime
from google import genai
from google.genai import types
import streamlit as st

# 1. Configuración de la interfaz
st.set_page_config(page_title="TutorFARO", page_icon="🔬")
st.title("🔬 Tutor de Prácticas de Laboratorio")
st.write("Resuelve tus dudas sobre los guiones antes de la sesión presencial.")

# 2. Obtención y validación de la API Key
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error(
        "⚠️ Falta la clave API. Ve a Settings > Secrets en Streamlit Cloud e introduce GEMINI_API_KEY."
    )
    st.stop()

# 3. Inicializar el cliente de Gemini
client = genai.Client(api_key=api_key)

# 4. Instrucciones del sistema (Prompt socrático)
SYSTEM_INSTRUCTION = """
Eres "TutorFARO", un tutor académico especializado en guiar a estudiantes 
de asignaturas experimentales en la preparación de sus guiones de laboratorio.

REGLAS:
- Método Socrático: No des soluciones o fórmulas de forma directa. Haz preguntas para que el alumno razone.
- Pide siempre al estudiante que explique qué ha intentado o comprendido del guion.
- Mantén respuestas breves, estructuradas y empáticas.
"""


# 5. Función para guardar los registros
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


# 6. Inicializar el historial de la sesión en Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar el historial de conversación en pantalla
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 7. Entrada de usuario y generación de respuesta
if prompt := st.chat_input("Escribe aquí tu duda sobre el guion..."):
    # Mostrar y guardar el mensaje del alumno
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    guardar_registro("estudiante", prompt)

    # Convertir el historial de Streamlit al formato nativo de Gemini
    contents = []
    for m in st.session_state.messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role, parts=[types.Part.from_text(text=m["content"])]
            )
        )

    # Configuración de generación usando el modelo oficial estable
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.3,
    )

    # Enviar la consulta a Gemini
    with st.chat_message("assistant"):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=contents, config=config
            )
            respuesta_texto = response.text
            st.markdown(respuesta_texto)

            # Guardar la respuesta en la sesión y en los registros
            st.session_state.messages.append(
                {"role": "assistant", "content": respuesta_texto}
            )
            guardar_registro("tutor", respuesta_texto)

        except Exception as e:
            st.error(
                f"Error al conectar con la API de Gemini: {e}\n\nPor favor, revisa que tu GEMINI_API_KEY en los Secrets de Streamlit sea válida."
            )

# Botón inferior para descargar el archivo de datos anonimizados
if os.path.exists("registro_dudas.json"):
    with open("registro_dudas.json", "r", encoding="utf-8") as f:
        datos_json = f.read()

    st.download_button(
        label="📥 Descargar registros (JSON)",
        data=datos_json,
        file_name="registro_dudas.json",
        mime="application/json",
    )
