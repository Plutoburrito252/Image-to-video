import json
import os
import time
import uuid
from pathlib import Path

import requests
import streamlit as st

# --------------------------------------------------
# Einstellungen
# --------------------------------------------------

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
WORKFLOW_FILE = BASE_DIR / "workflows" / "image_to_video.json"

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# ComfyUI-Funktionen
# --------------------------------------------------

def upload_image(image_bytes, filename):
    """Bild zu ComfyUI hochladen."""
    response = requests.post(
        f"{COMFYUI_URL}/upload/image",
        files={
            "image": (
                filename,
                image_bytes,
                "application/octet-stream"
            )
        },
        data={
            "overwrite": "true"
        },
        timeout=60
    )

    response.raise_for_status()
    return response.json()["name"]


def load_workflow():
    """Workflow aus JSON laden."""
    with open(WORKFLOW_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def find_node(workflow, class_type):
    """Ersten Node eines bestimmten Typs finden."""
    for node_id, node in workflow.items():
        if node.get("class_type") == class_type:
            return node_id, node

    return None, None


def prepare_workflow(image_name, prompt):
    """
    Workflow vorbereiten.

    Der Workflow muss einen LoadImage-Node besitzen.
    Der Prompt wird in einen CLIPTextEncode-Node geschrieben.
    """

    workflow = load_workflow()

    # Bild einsetzen
    image_node_id, image_node = find_node(workflow, "LoadImage")

    if image_node:
        image_node["inputs"]["image"] = image_name

    # Prompt einsetzen
    prompt_node_id, prompt_node = find_node(
        workflow,
        "CLIPTextEncode"
    )

    if prompt_node:
        prompt_node["inputs"]["text"] = prompt

    return workflow


def queue_prompt(workflow):
    """Workflow in ComfyUI starten."""
    client_id = str(uuid.uuid4())

    response = requests.post(
        f"{COMFYUI_URL}/prompt",
        json={
            "prompt": workflow,
            "client_id": client_id
        },
        timeout=60
    )

    response.raise_for_status()
    return response.json()["prompt_id"]


def wait_for_result(prompt_id):
    """Auf das fertige Video warten."""
    progress = st.progress(0)
    status = st.empty()

    for i in range(600):
        time.sleep(1)

        response = requests.get(
            f"{COMFYUI_URL}/history/{prompt_id}",
            timeout=30
        )

        if response.status_code != 200:
            continue

        history = response.json()

        if prompt_id not in history:
            progress.progress(min(i / 600, 0.99))
            status.info("KI generiert das Video ...")
            continue

        result = history[prompt_id]

        if result.get("status", {}).get("status_str") == "error":
            raise RuntimeError("ComfyUI konnte das Video nicht generieren.")

        outputs = result.get("outputs", {})

        for node_output in outputs.values():
            videos = node_output.get("gifs", [])
            videos += node_output.get("videos", [])

            if videos:
                video = videos[0]

                filename = video["filename"]
                subfolder = video.get("subfolder", "")
                folder_type = video.get("type", "output")

                if folder_type == "temp":
                    base_url = f"{COMFYUI_URL}/view"
                else:
                    base_url = f"{COMFYUI_URL}/view"

                video_response = requests.get(
                    base_url,
                    params={
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": folder_type
                    },
                    timeout=120
                )

                video_response.raise_for_status()

                output_path = OUTPUT_DIR / f"{prompt_id}.mp4"

                with open(output_path, "wb") as file:
                    file.write(video_response.content)

                progress.progress(1.0)
                status.success("Video fertig!")

                return output_path

    raise TimeoutError("Die Generierung hat zu lange gedauert.")


# --------------------------------------------------
# Weboberfläche
# --------------------------------------------------

st.set_page_config(
    page_title="Bild zu Video KI",
    page_icon="🎬",
    layout="centered"
)

st.title("🎬 Bild zu Video KI")
st.write("Verwandle ein Bild mit KI in ein kurzes Video.")

st.sidebar.header("Einstellungen")

duration = st.sidebar.slider(
    "Videolänge",
    min_value=2,
    max_value=10,
    value=5,
    help="Die tatsächliche Länge hängt vom verwendeten Modell ab."
)

motion_strength = st.sidebar.slider(
    "Bewegungsstärke",
    min_value=1,
    max_value=10,
    value=5
)

uploaded_file = st.file_uploader(
    "Bild hochladen",
    type=["png", "jpg", "jpeg", "webp"]
)

prompt = st.text_area(
    "Was soll sich bewegen?",
    placeholder=(
        "Eine sanfte Kamerafahrt nach vorne, "
        "natürliche Bewegungen, realistische Beleuchtung"
    ),
    height=100
)

negative_prompt = st.text_area(
    "Negative Prompt (optional)",
    placeholder="Unschärfe, Flackern, deformierte Hände ..."
)

generate = st.button(
    "🎥 Video generieren",
    use_container_width=True
)

if uploaded_file:
    st.image(
        uploaded_file,
        caption="Ausgangsbild",
        use_container_width=True
    )

if generate:

    if not uploaded_file:
        st.error("Bitte zuerst ein Bild hochladen.")

    elif not prompt.strip():
        st.error("Bitte beschreibe die gewünschte Bewegung.")

    else:
        try:
            with st.spinner("Bild wird vorbereitet ..."):

                image_bytes = uploaded_file.getvalue()

                image_name = upload_image(
                    image_bytes,
                    uploaded_file.name
                )

                workflow = prepare_workflow(
                    image_name,
                    prompt
                )

                # Falls dein Workflow diese Werte besitzt,
                # kannst du sie hier anpassen.
                for node in workflow.values():

                    inputs = node.get("inputs", {})

                    if "length" in inputs:
                        inputs["length"] = duration

                    if "motion_bucket_id" in inputs:
                        inputs["motion_bucket_id"] = motion_strength

                    if "negative_prompt" in inputs:
                        inputs["negative_prompt"] = negative_prompt

                prompt_id = queue_prompt(workflow)

                video_path = wait_for_result(prompt_id)

            st.video(str(video_path))

            with open(video_path, "rb") as video_file:
                st.download_button(
                    "⬇️ Video speichern",
                    data=video_file,
                    file_name="ki_video.mp4",
                    mime="video/mp4",
                    use_container_width=True
                )

        except requests.exceptions.ConnectionError:
            st.error(
                "ComfyUI wurde nicht gefunden. "
                "Starte zuerst ComfyUI."
            )

        except Exception as error:
            st.error(f"Fehler: {error}")