# Image-to-video
🎬 Bild zu Video KI

Ein lokaler Bild-zu-Video-Generator mit eigener Weboberfläche.

Funktionen

- Bild hochladen
- Bewegung beschreiben
- Videolänge einstellen
- Bewegungsstärke einstellen
- KI-Video generieren
- Video im Browser ansehen
- Video speichern

Voraussetzungen

- Windows / Linux / macOS
- Python 3.10 oder neuer
- ComfyUI
- Ein kompatibles Bild-zu-Video-Modell
- NVIDIA-Grafikkarte empfohlen

Installation

1. Repository klonen

git clone https://github.com/DEIN-NAME/bild-zu-video.git
cd bild-zu-video

2. Virtuelle Umgebung erstellen

python -m venv .venv

Windows:

.venv\Scripts\activate

3. Abhängigkeiten installieren

pip install -r requirements.txt

4. ComfyUI starten

ComfyUI muss auf diesem Port laufen:

http://127.0.0.1:8188

5. Workflow einrichten

Lege deinen Bild-zu-Video-Workflow hier ab:

workflows/image_to_video.json

Der Workflow muss mindestens einen "LoadImage"-Node besitzen.

6. Weboberfläche starten

streamlit run app.py

Danach öffnet sich die Oberfläche im Browser.

Lizenz

MIT