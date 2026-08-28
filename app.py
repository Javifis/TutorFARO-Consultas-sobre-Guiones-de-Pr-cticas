import glob
import json
import os
from datetime import datetime
from google import genai
from google.genai import types
from google.genai.errors import APIError
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


# 4. Función para cargar MÚLTIPLES PDF desde la carpeta 'documentos' (con caché de Streamlit)
@st.cache_resource
def cargar_documentos_pdf(carpeta_pdf="documentos"):
    archivos_procesados = []
    patron = os.path.join(carpeta_pdf, "*.pdf")
    lista_pdf = glob.glob(patron)

    if not lista_pdf:
        return []

    for ruta in lista_pdf:
        try:
            doc_subido = client.files.upload(file=ruta)
            archivos_procesados.append(doc_subido)
        except Exception as e:
            st.error(f"Error al subir {ruta} a Gemini: {e}")

    return archivos_procesados


# Cargar los PDF de la carpeta "documentos" al iniciar la app
documentos_contexto = cargar_documentos_pdf("documentos")

# 5. Instrucciones del sistema (Prompt socrático)
SYSTEM_INSTRUCTION = """
Eres "TutorFARO", un tutor académico inteligente especializado en guiar a estudiantes universitarios de asignaturas experimentales (como Física, Ondas y Electromagnetismo) en la preparación previa de sus guiones de laboratorio.
Tu objetivo es facilitar una lectura activa del material, asegurar la comprensión de los fundamentos teóricos y el procedimiento experimental, y resolver dudas sin dar las respuestas de forma directa.

[METODOLOGÍA PEDAGÓGICA Y PRINCIPIOS]
1. Método Socrático y Andamiaje: No proporciones la solución directa a un cálculo, fórmula o duda conceptual. Responde con preguntas guía que ayuden al estudiante a razonar, descomponer el problema y deducir el paso siguiente por sí mismo.
2. Lectura Activa e Interactiva: Transforma la lectura del guion en un diálogo. Si el estudiante te hace una pregunta general, verifica primero su punto de partida preguntándole qué ha entendido del guion o cuál es su hipótesis inicial.
3. Retroalimentación Formativa: Explica el "porqué" de los fenómenos físicos o procedimentales. Si el estudiante comete un error, ayuda a identificar la causa mediante ejemplos analógicos o contraejemplos.
4. Adaptabilidad y Flexibilidad: Ajusta la profundidad, notación y ejemplos al ritmo y nivel demostrado por el estudiante (enseñanza diferenciada).
5. Uso de los Guiones Adjuntos: Consulta la información, procedimientos, instrumentación y fórmulas presentes en los documentos PDF adjuntos para basar tus explicaciones y preguntas.

[INSTRUCCIONES OPERATIVAS Y REGLAS DIRECTIVAS]
- Si un estudiante pregunta "Cómo se hace X paso del guion" o "Cuál es la fórmula para Y", responde preguntándole qué datos identifica en el guion o qué ley física cree que aplica a esa situación.
- Prioriza la seguridad y la correcta manipulación de equipos: cuando la consulta involucre instrumental o procedimientos delicados del laboratorio, resalta los aspectos de seguridad e instrumentación clave descritos en el guion.
- Si el estudiante muestra frustración o bloqueo, descompón la pregunta en un subproblema mucho más sencillo para guiarlo paso a paso.
- Utiliza una notación científica y matemática clara, rigurosa y concisa.

[ESTILO Y TONO]
- Tono: Empático, motivador, riguroso, paciente y profesional. Trata al estudiante como un investigador en formación.
- Formato: Respuestas breves o estructuradas en listas cortas. Evita párrafos largos e ininterrumpidos para no sobrecargar cognitivamente al alumno antes de su práctica.

[EJEMPLO DE INTERACCIÓN ESPERADA]
Estudiante: "No entiendo qué tengo que medir en el paso 3 del guion de Ondas."
TutorFARO: "¡Hola! Revisemos ese paso juntos. Antes de mirar la medida concreta, ¿qué fenómeno físico estamos intentando observar en ese montaje y qué instrumento tienes conectado al circuito? Cuéntame qué entiendes de esa parte y lo construimos desde ahí."
"""


# 6. Función para guardar los registros
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


# 7. Inicializar el historial de la sesión en Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar el historial de conversación en pantalla
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 8. Entrada de usuario y generación de respuesta
if prompt := st.chat_input("Escribe aquí tu duda sobre el guion..."):
    # Mostrar y guardar el mensaje del alumno
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    guardar_registro("estudiante", prompt)

    # Construir el contenido enviando los PDF cargados en el primer bloque del contexto
    contents = []

    if documentos_contexto:
        partes_iniciales = list(documentos_contexto)
        partes_iniciales.append(
            types.Part.from_text(
                text="Utiliza los guiones PDF anteriores como base de conocimiento de la asignatura."
            )
        )
        contents.append(types.Content(role="user", parts=partes_iniciales))

    # Añadir los mensajes del historial
    for m in st.session_state.messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role, parts=[types.Part.from_text(text=m["content"])]
            )
        )

    # Configuración de generación
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.3,
    )

    # Generación de respuesta con manejo de errores y fallback de modelos
    with st.chat_message("assistant"):
        respuesta_texto = None
        modelos_disponibles = [
            "gemini-3.6-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ]

        for mod in modelos_disponibles:
            try:
                response = client.models.generate_content(
                    model=mod, contents=contents, config=config
                )
                respuesta_texto = response.text
                break
            except APIError as e:
                if (
                    "503" in str(e)
                    or "UNAVAILABLE" in str(e)
                    or "high demand" in str(e)
                ):
                    continue
                else:
                    st.error(f"Error en la API de Gemini: {e}")
                    break
            except Exception as e:
                st.error(f"Error inesperado: {e}")
                break

        if respuesta_texto:
            st.markdown(respuesta_texto)
            st.session_state.messages.append(
                {"role": "assistant", "content": respuesta_texto}
            )
            guardar_registro("tutor", respuesta_texto)
        elif not respuesta_texto:
            st.warning(
                "⏳ El servidor tiene alta demanda en este momento. Por favor, vuelve a enviar tu duda en unos segundos."
            )

# 9. Sección de administración para el profesor
st.divider()

with st.expander("🔐 Acceso Profesor"):
    clave_profesor = st.text_input(
        "Introduce la clave de acceso:", type="password"
    )

    if clave_profesor == "MiClaveSegura2026":
        if os.path.exists("registro_dudas.json"):
            with open("registro_dudas.json", "r", encoding="utf-8") as f:
                datos_json = f.read()

            st.download_button(
                label="📥 Descargar historial anonimizado (JSON)",
                data=datos_json,
                file_name="registro_dudas.json",
                mime="application/json",
            )
        else:
            st.info("Aún no hay registros guardados.")
    elif clave_profesor != "":
        st.error("Clave incorrecta.")
