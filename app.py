import io
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# =========================================================
# CONFIGURACIÓN
# =========================================================

APP_DIR = Path(__file__).parent
DATA_FILE = APP_DIR / "data" / "asignaciones_unidad4.csv"

NOMBRE_CARPETA_DRIVE = "Evaluacion_Oral_U4"


# =========================================================
# ESTRUCTURAS ANATÓMICAS
# =========================================================

ESTRUCTURAS = {
    "traquea": {
        "nombre": "Tráquea",
        "imagen": "images/traquea.png",
        "consigna": (
            "Observa la imagen. Graba un audio de aproximadamente 45 a 60 segundos "
            "describiendo la tráquea: indica su extensión por niveles vertebrales, "
            "sus componentes morfológicos cartilaginosos y musculares, y su relación "
            "anatómica inmediata de vecindad."
        ),
        "checklist": [
            "Extensión de la tráquea mediante niveles vertebrales.",
            "Componentes cartilaginosos.",
            "Componente muscular.",
            "Una relación anatómica inmediata de vecindad.",
            "Terminología anatómica apropiada para describir localización y relaciones.",
        ],
    },

    "laringe": {
        "nombre": "Laringe",
        "imagen": "images/laringe.png",
        "consigna": (
            "Graba un audio de aproximadamente 45 a 60 segundos sobre la laringe: "
            "especifica su localización por niveles vertebrales, la clasificación "
            "de sus cartílagos principales y la estructura interna de la glotis."
        ),
        "checklist": [
            "Localización mediante niveles vertebrales.",
            "Principales cartílagos laríngeos y su clasificación.",
            "Estructura interna de la glotis.",
            "Terminología anatómica apropiada para describir localización y componentes.",
        ],
    },

    "bronquios_carina": {
        "nombre": "Bronquios principales y carina traqueal",
        "imagen": "images/bronquios.png",
        "consigna": (
            "Graba un audio de aproximadamente 45 a 60 segundos describiendo la "
            "bifurcación traqueal: ubica la carina, compara la asimetría geométrica "
            "de ambos bronquios principales y menciona una relación vascular o "
            "esofágica de vecindad."
        ),
        "checklist": [
            "Localización de la carina traqueal.",
            "Descripción de la bifurcación de la tráquea.",
            "Comparación de la geometría de los bronquios principales derecho e izquierdo.",
            "Una relación anatómica vascular o esofágica de vecindad.",
            "Terminología anatómica apropiada para establecer la comparación.",
        ],
    },

    "faringe": {
        "nombre": "Faringe",
        "imagen": "images/faringe.png",
        "consigna": (
            "Graba un audio de aproximadamente 45 a 60 segundos describiendo la "
            "faringe: menciona su extensión vertebral, la división en sus 3 porciones "
            "con sus límites y el tipo de epitelio macroscópico según su función."
        ),
        "checklist": [
            "Extensión mediante niveles vertebrales.",
            "Identificación de las tres porciones de la faringe.",
            "Límites de cada porción.",
            "Tipo de epitelio relacionado con la función de cada región.",
            "Terminología anatómica apropiada.",
        ],
    },

    "cavidad_nasal": {
        "nombre": "Cavidad nasal",
        "imagen": "images/cavidadnasal.png",
        "consigna": (
            "Graba un audio de aproximadamente 45 a 60 segundos sobre la cavidad "
            "nasal: detalla los componentes del tabique nasal en su pared medial, "
            "las estructuras de la pared lateral y sus límites de entrada y salida."
        ),
        "checklist": [
            "Componentes del tabique nasal en la pared medial.",
            "Principales estructuras de la pared lateral.",
            "Límites de entrada de la cavidad nasal.",
            "Límites o comunicación de salida de la cavidad nasal.",
            "Terminología anatómica apropiada.",
        ],
    },

    "pulmones": {
        "nombre": "Pulmones derecho e izquierdo",
        "imagen": "images/pulmones.png",
        "consigna": (
            "Graba un audio de aproximadamente 45 a 60 segundos comparando ambos "
            "pulmones: detalla lóbulos, fisuras y características exclusivas del "
            "pulmón izquierdo, así como la posición de los vértices y bases."
        ),
        "checklist": [
            "Comparación de la morfología de ambos pulmones.",
            "Lóbulos de cada pulmón.",
            "Fisuras correspondientes.",
            "Características exclusivas o distintivas del pulmón izquierdo.",
            "Posición de los vértices y bases.",
            "Terminología anatómica apropiada para realizar la comparación.",
        ],
    },
}


# =========================================================
# CONEXIÓN CON GOOGLE DRIVE
# =========================================================

def conectar_drive():

    config = st.secrets["gcp_oauth"]

    credentials = Credentials(
        token=None,
        refresh_token=config["refresh_token"],
        token_uri=config["token_uri"],
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        scopes=config["scopes"],
    )

    service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    return service


def obtener_carpeta_drive(service):

    nombre = NOMBRE_CARPETA_DRIVE

    resultado = service.files().list(
        q=(
            f"name='{nombre}' "
            "and mimeType='application/vnd.google-apps.folder' "
            "and trashed=false"
        ),
        spaces="drive",
        fields="files(id, name)",
    ).execute()

    carpetas = resultado.get("files", [])

    if carpetas:
        return carpetas[0]["id"]

    carpeta = service.files().create(
        body={
            "name": nombre,
            "mimeType": "application/vnd.google-apps.folder",
        },
        fields="id",
    ).execute()

    return carpeta["id"]


def guardar_archivo_drive(
    service,
    carpeta_id,
    nombre,
    contenido,
    mime_type,
):

    archivo = {
        "name": nombre,
        "parents": [carpeta_id],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(contenido),
        mimetype=mime_type,
        resumable=True,
    )

    resultado = service.files().create(
        body=archivo,
        media_body=media,
        fields="id, name",
    ).execute()

    return resultado


# =========================================================
# INTERFAZ
# =========================================================

st.set_page_config(
    page_title="Evaluación Oral U4 · Aparato Respiratorio",
    page_icon="🫁",
    layout="centered",
)

st.title("Evaluación oral · Unidad 4")
st.subheader("Aparato respiratorio")

st.markdown(
    """
**Instrucciones generales**

Recibirás de manera aleatoria una estructura anatómica del aparato respiratorio
acompañada de una imagen. Deberás realizar una descripción oral siguiendo los
elementos indicados en la consigna.

Tu respuesta debe ser **breve, organizada y tener una duración aproximada de 45 a 60 segundos**.

Puedes utilizar un **mapa conceptual, palabras clave o una escaleta** para organizar
tus ideas antes de realizar la grabación.

**No está permitido utilizar un script o texto redactado para leer durante la
grabación.** La respuesta debe ser espontánea y demostrar tu dominio del contenido
anatómico.
"""
)


# =========================================================
# CARGAR ASIGNACIONES
# =========================================================

@st.cache_data
def cargar_asignaciones():

    df = pd.read_csv(
        DATA_FILE,
        dtype={
            "id": str,
            "estructura_id": str,
        },
    )

    df["id"] = df["id"].str.strip().str.zfill(8)
    df["estructura_id"] = df["estructura_id"].str.strip().str.zfill(2)

    return df


df = cargar_asignaciones()

st.divider()


# =========================================================
# IDENTIFICACIÓN DEL ESTUDIANTE
# =========================================================

student_id = st.text_input(
    "Ingresa tu ID",
    max_chars=8,
    placeholder="Ejemplo: 00554053",
)

if student_id:

    student_id = student_id.strip().zfill(8)

    alumno = df[df["id"] == student_id]

    if alumno.empty:
        st.error(
            "El ID no se encuentra en la lista de estudiantes de esta evaluación."
        )
        st.stop()

    row = alumno.iloc[0]
    key = row["estructura"]

    if key not in ESTRUCTURAS:
        st.error(
            "No se encontró la configuración de la estructura asignada."
        )
        st.stop()

    actividad = ESTRUCTURAS[key]

    st.success("ID reconocido.")

    nombre_alumno = (
        str(row["nombre_completo"])
        if pd.notna(row["nombre_completo"])
        else ""
    )

    if nombre_alumno.strip():
        st.write(f"**Alumno:** {nombre_alumno}")

    st.info(
        f"**Tu estructura asignada:** {actividad['nombre']}"
    )

    st.image(
        actividad["imagen"],
        use_container_width=True,
    )

    st.markdown("### Consigna")
    st.write(actividad["consigna"])

    # -----------------------------------------------------
    # CHECKLIST
    # -----------------------------------------------------

    st.markdown("### Antes de grabar")

    checklist_resultados = {}

    for i, item in enumerate(actividad["checklist"]):

        checklist_resultados[item] = st.checkbox(
            item,
            key=f"check_{student_id}_{key}_{i}",
        )

    # -----------------------------------------------------
    # PREPARACIÓN
    # -----------------------------------------------------

    st.markdown("### Preparación de la respuesta")

    st.markdown(
        """
Puedes apoyarte en **palabras clave, una escaleta o un mapa conceptual**.

**No leas un script.** La lectura de un texto previamente redactado se considerará
una respuesta no espontánea y se reflejará en el criterio **Elaboración espontánea
de la respuesta** de la rúbrica.
"""
    )

    # -----------------------------------------------------
    # GRABACIÓN
    # -----------------------------------------------------

    st.markdown("### Grabación")

    audio = st.audio_input(
        "Graba tu respuesta",
        key=f"audio_{student_id}_{key}",
        sample_rate=44100,
    )

    if audio is not None:

        st.audio(audio)

        st.warning(
            "Revisa tu grabación antes de enviarla. Verifica que tu respuesta sea "
            "clara, espontánea y que incluya los elementos solicitados."
        )

        confirm = st.checkbox(
            "He revisado mi grabación y deseo enviarla.",
            key=f"confirm_{student_id}_{key}",
        )

        enviado_key = f"enviado_{student_id}_{key}"

        if st.session_state.get(enviado_key, False):

            st.success(
                "Tu respuesta ya fue enviada correctamente."
            )

        elif confirm:

            if st.button(
                "Enviar respuesta",
                type="primary",
                key=f"submit_{student_id}_{key}",
            ):

                try:

                    with st.spinner(
                        "Guardando tu respuesta. No cierres esta página..."
                    ):

                        service = conectar_drive()

                        carpeta_id = obtener_carpeta_drive(service)

                        fecha = datetime.now().astimezone()

                        marca_tiempo = fecha.strftime(
                            "%Y%m%d_%H%M%S"
                        )

                        audio_bytes = audio.getvalue()

                        mime_type = audio.type or "audio/webm"

                        extensiones = {
                            "audio/webm": "webm",
                            "audio/wav": "wav",
                            "audio/mp4": "mp4",
                            "audio/ogg": "ogg",
                            "audio/mpeg": "mp3",
                        }

                        extension = extensiones.get(
                            mime_type,
                            "audio",
                        )

                        audio_nombre = (
                            f"{student_id}_{key}_{marca_tiempo}.{extension}"
                        )

                        archivo_audio = guardar_archivo_drive(
                            service=service,
                            carpeta_id=carpeta_id,
                            nombre=audio_nombre,
                            contenido=audio_bytes,
                            mime_type=mime_type,
                        )

                        registro = {
                            "id": student_id,
                            "nombre": nombre_alumno,
                            "estructura": actividad["nombre"],
                            "estructura_id": key,
                            "fecha_hora": fecha.isoformat(),
                            "audio_archivo": archivo_audio["name"],
                            "audio_drive_id": archivo_audio["id"],
                            "checklist": checklist_resultados,
                        }

                        registro_bytes = json.dumps(
                            registro,
                            ensure_ascii=False,
                            indent=2,
                        ).encode("utf-8")

                        guardar_archivo_drive(
                            service=service,
                            carpeta_id=carpeta_id,
                            nombre=(
                                f"{student_id}_{key}_{marca_tiempo}.json"
                            ),
                            contenido=registro_bytes,
                            mime_type="application/json",
                        )

                    st.session_state[enviado_key] = True

                    st.success(
                        "Tu respuesta fue enviada correctamente."
                    )

                    st.info(
                        "Puedes cerrar esta página. Tu grabación fue guardada."
                    )

                except Exception:

                    st.error(
                        "No se pudo guardar tu respuesta. "
                        "Por favor, informa a tu docente."
                    )

                    st.exception(Exception(
                        "Error durante el envío a Google Drive. "
                        "Revisa los registros de la aplicación en Streamlit Cloud."
                    ))
