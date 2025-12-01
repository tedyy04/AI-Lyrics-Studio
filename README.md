# AI Audio Studio – Vocal Separator & Transcriber

> Turn any song or podcast into ready‑to‑use lyrics and subtitles in a few clicks.

AI Audio Studio is a full‑stack web application that bridges the gap between **raw audio** and **usable content**.  
It provides a modern “liquid glass” style UI (with a pink–purple gradient palette) and leverages state‑of‑the‑art AI models to process audio in two distinct modes: **Song / Music** and **Podcast**.

---

## Features

### 🎵 Song / Music Mode

- **Vocal isolation** – Uses **Demucs** (by Meta) to separate vocals from background music.
- **Lyrics generation** – Runs **OpenAI Whisper** on the isolated vocal track to generate synchronized lyrics.
- **Synced player** – Click on any lyric line to jump to that specific timestamp (Apple Music / Spotify style).

### 🎙️ Podcast Mode

- **High‑fidelity transcription** – Uses **OpenAI Whisper** to transcribe speech to text with high accuracy.
- **Multi‑format export** – Download transcripts in:
  - `.txt`
  - `.srt`
  - `.vtt`
  - `.lrc`

### UI / UX

- **Liquid Glass design** – Soft glassmorphism cards on top of a pink–purple gradient background.
- **Dual modes** – Song vs Podcast selection directly on the upload screen.
- **Segment timeline** – Visual markers for each lyric/transcript segment on the progress bar.
- **Clickable lyrics** – Seek the audio by clicking on any line of text.

> *(Optional / nice‑to‑have)*  
> Audio visualizer and in‑app help/guide can be added on top of this base.

---

## Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** HTML5, Vanilla JavaScript, TailwindCSS (via CDN) or custom CSS
- **AI Models:** Demucs, OpenAI Whisper
- **Audio Processing:** FFmpeg, Pydub, Torchaudio / SoundFile

---

## Prerequisites

Before running the project, make sure you have:

- **Python 3.8+**
- **FFmpeg** (critical for audio processing)

Install FFmpeg:

- **macOS:**

  ```bash
  brew install ffmpeg
  ```

- **Ubuntu / Debian:**

  ```bash
  sudo apt update
  sudo apt install ffmpeg
  ```

- **Windows:**  
  Download the FFmpeg build from the official site, unzip, and add the `bin` folder to your **PATH**.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/tedyy04/AI-Lyrics-Studio.git
cd AI-Lyrics-Studio
```

### 2. Create & activate a virtual environment

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell / CMD):**

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

If you don’t use a `requirements.txt`, you can install directly:

```bash
pip install fastapi uvicorn python-multipart jinja2 torch openai-whisper demucs pydub aiofiles soundfile
```

> `soundfile` is often required to fix backend I/O errors on macOS/Linux.

---

## Running the App

Start the FastAPI server:

```bash
uvicorn main:app --reload --port 8000
```

Open your browser and go to:

- **http://localhost:8000**

Typical flow:

1. **Home page** (`/`) – Landing / documentation (optional).
2. Click **“Launch Studio”** → opens the main upload interface (`/app`).
3. Select **mode** (Song / Podcast), choose an audio file (`< 60 minutes`), and click **“Upload & start”**.
4. Wait while the job is processed (status polling).
5. You’ll be redirected to `/result/{job_id}` with:
   - A custom player (vocal track for songs, full audio for podcasts).
   - Scrollable, auto‑highlighted lyrics/transcript.
   - Download buttons for TXT / SRT / VTT / LRC.

---

## Project Structure

```text
.
├── main.py              # FastAPI backend & application logic
├── uploads/             # Uploaded & processed audio files
├── results/             # Per‑job outputs (subtitles, text, etc.)
├── static/
│   └── styles.css       # Liquid glass / gradient theme styles
├── templates/
│   ├── help.html        # Optional landing / documentation page
│   ├── index.html       # Upload interface (mode + file)
│   └── result.html      # Result page (player + lyrics / transcript)
├── requirements.txt     # Python dependencies
└── README.md            # Project documentation
```

> Make sure `uploads/` and `results/` are created (and writable) before running the server.

---

## Troubleshooting

| Error message                                            | Cause                        | Fix                                                                 |
|----------------------------------------------------------|-----------------------------|---------------------------------------------------------------------|
| `FileNotFoundError: ... 'ffmpeg'`                        | FFmpeg is missing           | Install FFmpeg and ensure it is on your system `PATH`.              |
| `RuntimeError: Couldn't find appropriate backend`        | Missing audio backend       | Run `pip install soundfile` (and optionally `pip install torchaudio`). |
| `Demucs exited with status 1`                            | Demucs subprocess failure   | Check FFmpeg installation, model download, and run inside `venv`.   |
| Git push errors for large files                          | Huge audio/output files     | Add `uploads/`, `results/`, and `venv/` to `.gitignore`.            |

Example `.gitignore` snippet:

```gitignore
venv/
__pycache__/
uploads/
results/
*.log
```

---

## License

This project is intended for **learning, experimentation, and portfolio use**.  
---

Happy building – and enjoy turning your audio into beautiful, synced text.
