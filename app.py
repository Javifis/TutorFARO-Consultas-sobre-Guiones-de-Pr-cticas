import time

# ... (resto del código sin cambios)

# 8. Entrada de usuario y generación de respuesta
if prompt := st.chat_input("Escribe aquí tu duda sobre el guion..."):
    # Mostrar y guardar el mensaje del alumno
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    guardar_registro("estudiante", prompt)

    # Construir la estructura de contenidos para la API
    contents = []

    # Incluir los documentos de contexto en el primer bloque
    if partes_documentos:
        partes_iniciales = list(partes_documentos)
        partes_iniciales.append(
            types.Part.from_text(
                text="Utiliza los guiones y documentos adjuntos anteriores como base de conocimiento primaria de la asignatura."
            )
        )
        contents.append(types.Content(role="user", parts=partes_iniciales))

    # Añadir los mensajes de la conversación
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

    # Generación de respuesta con reintentos automáticos en el modelo actual
    with st.chat_message("assistant"):
        respuesta_texto = None
        modelo_actual = "gemini-3.6-flash"
        max_reintentos = 3

        for intento in range(max_reintentos):
            try:
                response = client.models.generate_content(
                    model=modelo_actual, contents=contents, config=config
                )
                respuesta_texto = response.text
                break  # Éxito: salimos del bucle
            except APIError as e:
                # Si hay saturación o alta demanda (503 / UNAVAILABLE), esperamos 2 segundos y reintentamos
                if (
                    "503" in str(e)
                    or "UNAVAILABLE" in str(e)
                    or "high demand" in str(e)
                ):
                    time.sleep(2)
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
