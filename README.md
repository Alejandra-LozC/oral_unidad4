# Evaluación Oral U4 · Aparato Respiratorio

Aplicación Streamlit para la evaluación oral de la Unidad 4.

## Versión actual
- Identificación mediante ID.
- Asignación fija previamente generada.
- Seis estructuras anatómicas.
- Imagen individual por asignación.
- Consigna individual.
- Lista de cotejo interactiva.
- Grabación desde el navegador.
- Reproducción de la grabación.
- Preparada para integrar Google Drive en la siguiente etapa.

## Estructura
- `app.py`: aplicación principal.
- `data/asignaciones_unidad4.csv`: asignaciones definitivas.
- `images/`: imágenes anatómicas.
- `requirements.txt`: dependencias.

## Nota
El botón de envío está deliberadamente deshabilitado en esta primera versión.
Primero se probará el flujo alumno/asignación/grabación. Después se conectará
Google Drive para almacenar los audios.
