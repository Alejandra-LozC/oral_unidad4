import io
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Evaluación Oral U4 · Aparato Respiratorio",
    page_icon="🫁",
    layout="centered"
)

CARPETA_DRIVE = "Evaluacion_Oral_U4"
CSV_RESUMEN = "resumen_evaluaciones_u4.csv"

ARCHIVO_ASIGNACIONES = Path("data/asignaciones_unidad4.csv")


# ============================================================
# ESTRUCTURAS Y CRITERIOS
# ============================================================

ESTRUCTURAS = {
    "traquea": {
        "nombre": "Tráquea",
        "imagen": "images/traquea.png",
        "consigna": (
            "Describe la localización de la tráquea, sus relaciones "
            "anatómicas y sus características estructurales."
        ),
        "checklist": [
            "Localiza la tráquea utilizando términos anatómicos.",
            "Describe sus límites superior e inferior.",
            "Identifica los anillos cartilaginosos y la pared posterior.",
            "Describe su relación con el esófago.",
            "Explica su continuidad con la laringe y los bronquios principales."
        ]
    },
    "laringe": {
        "nombre": "Laringe",
        "imagen": "images/laringe.png",
        "consigna": (
            "Describe la localización, los límites y los componentes "
            "anatómicos de la laringe."
        ),
        "checklist": [
            "Localiza la laringe en la región cervical.",
            "Identifica sus límites superior e inferior.",
            "Menciona los principales cartílagos laríngeos.",
            "Describe la relación entre epiglotis, glotis y pliegues vocales.",
            "Explica su continuidad con la faringe y la tráquea."
        ]
    },
    "bronquios_carina": {
        "nombre": "Bronquios principales y carina",
        "imagen": "images/bronquios.png",
        "consigna": (
            "Describe la bifurcación de la tráquea, la carina y las "
            "características anatómicas de los bronquios principales."
        ),
        "checklist": [
            "Identifica el nivel aproximado de la bifurcación traqueal.",
            "Localiza la carina traqueal.",
            "Distingue el bronquio principal derecho del izquierdo.",
            "Describe las diferencias anatómicas entre ambos bronquios.",
            "Explica su continuidad con el árbol bronquial."
        ]
    },
    "faringe": {
        "nombre": "Faringe",
        "imagen": "images/faringe.png",
        "consigna": (
            "Describe la localización, los límites y las divisiones "
            "anatómicas de la faringe."
        ),
        "checklist": [
            "Localiza la faringe en relación con las cavidades nasal y oral.",
            "Identifica sus límites superior e inferior.",
            "Distingue nasofaringe, orofaringe y laringofaringe.",
            "Describe sus relaciones anterior y posterior.",
            "Explica su continuidad con el esófago y la laringe."
        ]
    },
    "cavidad_nasal": {
        "nombre": "Cavidad nasal",
        "imagen": "images/cavidadnasal.png",
        "consigna": (
            "Describe los límites, paredes y componentes anatómicos "
            "de la cavidad nasal."
        ),
        "checklist": [
            "Localiza la cavidad nasal respecto a la cavidad oral y la órbita.",
            "Describe sus límites anterior y posterior.",
            "Identifica el tabique nasal.",
            "Identifica los cornetes y meatos nasales.",
            "Describe su comunicación con la nasofaringe y los senos paranasales."
        ]
    },
    "pulmones": {
        "nombre": "Pulmones",
        "imagen": "images/pulmones.png",
        "consigna": (
            "Describe la localización, características externas y "
            "divisiones anatómicas de ambos pulmones."
        ),
        "checklist": [
            "Localiza los pulmones dentro de la cavidad torácica.",
            "Identifica ápice, base, caras y bordes.",
            "Describe las diferencias entre pulmón derecho e izquierdo.",
            "Identifica los lóbulos y las fisuras pulmonares.",
            "Describe la relación de los pulmones con la pleura y el mediastino."
        ]
    }
}


# ============================================================
# GOOGLE DRIVE
# ============================================================

@st.cache_resource
def conectar_drive():
    config = st.secrets["gcp_oauth"]

    credenciales = Credentials(
        token=None,
        refresh_token=config["refresh_token"],
        token_uri=config.get(
            "token_uri",
            "https://oauth2.googleapis.com/token"
        ),
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        scopes=config["scopes"]
    )

    return build(
        "drive",
        "v3",
        credentials=credenciales,
        cache_discovery=False
    )


def obtener_carpeta_drive(service):
    resultado = service.files().list(
        q=(
            f"name='{CARPETA_DRIVE}' "
            "and mimeType='application/vnd.google-apps.folder' "
            "and trashed=false"
        ),
        spaces="drive",
        fields="files(id,name)",
        pageSize=100
    ).execute()

    carpetas = resultado.get("files", [])

    if carpetas:
        return carpetas[0]["id"]

    metadata = {
        "name": CARPETA_DRIVE,
        "mimeType": "application/vnd.google-apps.folder"
    }

    carpeta = service.files().create(
        body=metadata,
        fields="id"
    ).execute()

    return carpeta["id"]


def buscar_archivo_drive(service, folder_id, filename):
    resultado = service.files().list(
        q=(
            f"name='{filename}' "
            f"and '{folder_id}' in parents "
            "and trashed=false"
        ),
        spaces="drive",
        fields="files(id,name,mimeType)",
        pageSize=100
    ).execute()

    archivos = resultado.get("files", [])

    return archivos[0] if archivos else None


def subir_archivo_drive(
    service,
    folder_id,
    filename,
    contenido,
    mimetype
):
    metadata = {
        "name": filename,
        "parents": [folder_id]
    }

    media = MediaIoBaseUpload(
        io.BytesIO(contenido),
        mimetype=mimetype,
        resumable=True
    )

    archivo = service.files().create(
        body=metadata,
        media_body=media,
        fields="id,name"
    ).execute()

    return archivo


def actualizar_archivo_drive(
    service,
    file_id,
    contenido,
    mimetype
):
    media = MediaIoBaseUpload(
        io.BytesIO(contenido),
        mimetype=mimetype,
        resumable=True
    )

    return service.files().update(
        fileId=file_id,
        media_body=media,
        fields="id,name"
    ).execute()


# ============================================================
# GUARDAR CSV CONSOLIDADO
# ============================================================

def guardar_resumen_drive(service, folder_id, registro):

    archivo_existente = buscar_archivo_drive(
        service,
        folder_id,
        CSV_RESUMEN
    )

    if archivo_existente:
        contenido_actual = service.files().get_media(
            fileId=archivo_existente["id"]
        ).execute()

        try:
            df_existente = pd.read_csv(
                io.BytesIO(contenido_actual),
                dtype=str
            ).fillna("")
        except Exception:
            df_existente = pd.DataFrame()

        df_nuevo = pd.DataFrame([registro])

        df_final = pd.concat(
            [df_existente, df_nuevo],
            ignore_index=True
        ).fillna("")

        contenido_csv = df_final.to_csv(
            index=False
        ).encode("utf-8-sig")

        actualizar_archivo_drive(
            service,
            archivo_existente["id"],
            contenido_csv,
            "text/csv"
        )

    else:
        df_nuevo = pd.DataFrame([registro])

        contenido_csv = df_nuevo.to_csv(
            index=False
        ).encode("utf-8-sig")

        subir_archivo_drive(
            service,
            folder_id,
            CSV_RESUMEN,
            contenido_csv,
            "text/csv"
        )


# ============================================================
# CARGAR ASIGNACIONES
# ============================================================

@st.cache_data
def cargar_asignaciones():
    if not ARCHIVO_ASIGNACIONES.exists():
        raise FileNotFoundError(
            "No se encontró data/asignaciones_unidad4.csv"
        )

    df = pd.read_csv(
        ARCHIVO_ASIGNACIONES,
        dtype=str
    ).fillna("")

    columnas_requeridas = {
        "id",
        "nombre_completo",
        "estructura_id",
        "estructura"
    }

    faltantes = columnas_requeridas - set(df.columns)

    if faltantes:
        raise ValueError(
            f"Faltan columnas en asignaciones_unidad4.csv: {faltantes}"
        )

    df["id"] = df["id"].str.strip().str.zfill(2)
    df["estructura_id"] = df["estructura_id"].str.strip()

    return df


# ============================================================
# INTERFAZ
# ============================================================

st.title("Evaluación Oral U4")
st.subheader("Aparato Respiratorio")

st.write(
    "Ingresa tu matrícula o identificador para consultar "
    "la estructura anatómica asignada."
)

try:
    asignaciones = cargar_asignaciones()
except Exception as e:
    st.error("No fue posible cargar el archivo de asignaciones.")
    st.exception(e)
    st.stop()


id_alumno = st.text_input(
    "Identificador del alumno",
    max_chars=20,
    placeholder="Ingresa tu identificador"
)

id_alumno = id_alumno.strip().zfill(2) if id_alumno.strip() else ""

if not id_alumno:
    st.info("Ingresa tu identificador para continuar.")
    st.stop()

alumno = asignaciones[
    asignaciones["id"] == id_alumno
]

if alumno.empty:
    st.error("No se encontró el identificador. Verifica los datos.")
    st.stop()

alumno = alumno.iloc[0]

nombre = alumno["nombre_completo"]
estructura_id = alumno["estructura_id"]

if estructura_id not in ESTRUCTURAS:
    st.error("La estructura asignada no está configurada.")
    st.stop()

estructura = ESTRUCTURAS[estructura_id]

st.success(f"Alumno: {nombre}")

st.markdown("---")

st.header(estructura["nombre"])

# Imagen y checklist lado a lado
col_imagen, col_checklist = st.columns(
    [1.15, 1],
    gap="large"
)

with col_imagen:
    st.image(
        estructura["imagen"],
        use_container_width=True
    )

    st.markdown("#### Consigna")

    st.write(estructura["consigna"])

with col_checklist:
    st.markdown("#### Lista de cotejo")

    st.caption(
        "Utiliza estos criterios para verificar que tu explicación "
        "incluya los elementos anatómicos solicitados."
    )

    respuestas = []

    for i, criterio in enumerate(
        estructura["checklist"],
        start=1
    ):
        respuesta = st.checkbox(
            criterio,
            key=f"{id_alumno}_{estructura_id}_criterio_{i}"
        )

        respuestas.append(respuesta)

st.markdown("---")

st.header("Preparación y grabación")

st.write(
    "Prepara tu respuesta utilizando terminología anatómica. "
    "Cuando estés listo, graba tu explicación."
)

audio = st.audio_input(
    "Grabar respuesta oral",
    sample_rate=44100
)

if audio is not None:
    st.audio(audio)

    st.caption(
        f"Audio capturado: {audio.name or 'Grabación de audio'}"
    )

todos_completos = all(respuestas)

if not todos_completos:
    st.warning(
        "Revisa los criterios de la lista de cotejo antes de enviar."
    )

if st.button(
    "Enviar evaluación",
    type="primary",
    use_container_width=True,
    disabled=audio is None
):

    try:
        service = conectar_drive()
        folder_id = obtener_carpeta_drive(service)

        fecha_hora = datetime.now().astimezone()
        marca_tiempo = fecha_hora.strftime("%Y%m%d_%H%M%S")

        audio_bytes = audio.getvalue()

        extension = "wav"
        if audio.type and "webm" in audio.type.lower():
            extension = "webm"
        elif audio.type and "ogg" in audio.type.lower():
            extension = "ogg"
        elif audio.type and "mp4" in audio.type.lower():
            extension = "mp4"

        audio_filename = (
            f"{id_alumno}_{estructura_id}_{marca_tiempo}.{extension}"
        )

        archivo_audio = subir_archivo_drive(
            service,
            folder_id,
            audio_filename,
            audio_bytes,
            audio.type or "audio/wav"
        )

        checklist_resultado = {
            f"criterio_{i}": (
                "Cumplido" if respuesta else "No marcado"
            )
            for i, respuesta in enumerate(respuestas, start=1)
        }

        registro_json = {
            "id": id_alumno,
            "nombre_completo": nombre,
            "estructura_id": estructura_id,
            "estructura": estructura["nombre"],
            "fecha_hora": fecha_hora.isoformat(),
            "audio_archivo": audio_filename,
            "audio_drive_id": archivo_audio["id"],
            "checklist": checklist_resultado
        }

        json_filename = (
            f"{id_alumno}_{estructura_id}_{marca_tiempo}.json"
        )

        archivo_json = subir_archivo_drive(
            service,
            folder_id,
            json_filename,
            json.dumps(
                registro_json,
                ensure_ascii=False,
                indent=2
            ).encode("utf-8"),
            "application/json"
        )

        registro_csv = {
            "id": id_alumno,
            "nombre_completo": nombre,
            "estructura_id": estructura_id,
            "estructura": estructura["nombre"],
            "fecha_hora": fecha_hora.isoformat(),
            "audio_archivo": audio_filename,
            "audio_drive_id": archivo_audio["id"],
            "json_archivo": json_filename,
            "json_drive_id": archivo_json["id"],
            "checklist_json": json.dumps(
                checklist_resultado,
                ensure_ascii=False
            ),
            **checklist_resultado
        }

        guardar_resumen_drive(
            service,
            folder_id,
            registro_csv
        )

        st.success("Evaluación enviada correctamente.")
        st.info(
            "Se guardaron la grabación, el registro individual "
            "y el resumen consolidado en Google Drive."
        )

    except Exception as e:
        st.error(
            "No fue posible completar el envío. "
            "Verifica la conexión con Google Drive."
        )
        st.exception(e)
