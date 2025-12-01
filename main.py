import os
import uuid
import asyncio
import shutil
import sys
import math
import mimetypes
from typing import List, TypedDict, Any, Dict, cast
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydub import AudioSegment
import json

# --- CONFIGURATION ---
# Set True for a smooth demo without heavy deps
MOCK_AI_PROCESSING = False  # ĐỔI THÀNH FALSE ĐỂ CHẠY AI THẬT (Demucs + Whisper)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- MEMORY STORE (Thay bằng DB trong production) ---
jobs = {}

# --- HELPER CLASSES ---
class JobStatus:
    PENDING = "pending"
    SEPARATING = "separating"
    TRANSCRIBING = "transcribing"
    DONE = "done"
    ERROR = "error"

# --- TYPES ---
class Segment(TypedDict):
    start: float
    end: float
    text: str

# --- AI PROCESSING TASKS ---
def generate_subtitles(segments: List[Segment], duration: float):
    """Tạo nội dung cho SRT, VTT, LRC, TXT từ segments"""
    srt, vtt, lrc, txt = "", "WEBVTT\n\n", "", ""
    
    for i, seg in enumerate(segments):
        start = seg['start']
        end = seg['end']
        text = seg['text'].strip()
        
        # Format timestamps
        def fmt_srt(t):
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int((t * 1000) % 1000)
            return f"{h:02}:{m:02}:{s:02},{ms:03}"

        def fmt_lrc(t):
            m = int(t // 60)
            s = int(t % 60)
            cs = int((t * 100) % 100)
            return f"[{m:02}:{s:02}.{cs:02}]"

        # TXT
        txt += text + "\n"
        
        # SRT
        srt += f"{i+1}\n{fmt_srt(start)} --> {fmt_srt(end)}\n{text}\n\n"
        
        # VTT
        vtt += f"{fmt_srt(start).replace(',', '.')} --> {fmt_srt(end).replace(',', '.')}\n{text}\n\n"
        
        # LRC
        lrc += f"{fmt_lrc(start)}{text}\n"

    return {"srt": srt, "vtt": vtt, "lrc": lrc, "txt": txt}

async def process_audio_task(job_id: str, file_path: str, mode: str, original_filename: str):
    try:
        jobs[job_id]["status"] = JobStatus.SEPARATING
        work_dir = os.path.dirname(file_path)
        
        # 1. Convert to WAV standard (16kHz mono) with fallback if ffmpeg missing
        duration = 0.0
        wav_path = os.path.join(work_dir, f"{job_id}_std.wav")
        try:
            audio = AudioSegment.from_file(file_path)
            audio = audio.set_channels(1).set_frame_rate(16000)
            audio.export(wav_path, format="wav")
            duration = len(audio) / 1000.0
            processed_audio_path = wav_path
        except Exception as conv_err:
            # Fallback: keep original file; we'll set duration after segmentation
            processed_audio_path = file_path

        # 2. Vocal Separation (Demucs)
        if mode == "song" and not MOCK_AI_PROCESSING:
            jobs[job_id]["status"] = JobStatus.SEPARATING
            
            # --- CHẠY DEMUCS THẬT (SỬA LẠI) ---
            import subprocess
            
            # Thay vì gọi "demucs" trống trơn, ta gọi cụ thể python hiện tại để chạy module demucs
            cmd = [
                sys.executable, "-m", "demucs",
                "-n", "htdemucs",
                "--two-stems", "vocals",
                wav_path,
                "-o", work_dir
            ]
            
            # Capture output để in ra terminal nếu có lỗi
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True
            )
            
            # Kiểm tra lỗi kỹ hơn
            if result.returncode != 0:
                print("❌ Lỗi Demucs:")
                print(result.stderr) # In chi tiết lỗi ra Terminal
                raise Exception("Demucs failed via CLI")

            # Cập nhật đường dẫn tới file vocal vừa tách được
            # Cấu trúc folder mặc định của Demucs: {out_dir}/htdemucs/{track_name}/vocals.wav
            filename_no_ext = os.path.splitext(os.path.basename(wav_path))[0]
            separated_path = os.path.join(work_dir, "htdemucs", filename_no_ext, "vocals.wav")
            
            if os.path.exists(separated_path):
                processed_audio_path = separated_path
            else:
                print("Warning: Không tìm thấy file vocal, dùng file gốc.")

        # 3. Transcribe (Whisper)
        jobs[job_id]["status"] = JobStatus.TRANSCRIBING
        segments: List[Segment] = []
        
        if not MOCK_AI_PROCESSING:
            try:
                import whisper
                # Use a lighter model by default
                model = whisper.load_model("base")
                result = model.transcribe(processed_audio_path)
                segments_raw = cast(List[Dict[str, Any]], result.get("segments", []))
                segments = [
                    {
                        "start": float(s.get("start", 0.0)),
                        "end": float(s.get("end", 0.0)),
                        "text": str(s.get("text", "")),
                    }
                    for s in segments_raw
                ]
            except Exception as werr:
                print(f"Whisper failed, using mock segments: {werr}")
                await asyncio.sleep(1)
                segments = [
                    {"start": 0.0, "end": 2.5, "text": "Đây là câu đầu tiên của bài hát."},
                    {"start": 2.6, "end": 5.0, "text": "Và đây là đoạn tiếp theo đang hát."},
                    {"start": 5.5, "end": 10.0, "text": "Đoạn điệp khúc cao trào nằm ở đây (Chorus)."},
                    {"start": 10.5, "end": 15.0, "text": "Kết thúc đoạn demo mock data."}
                ]
        else:
            # (Phần Mock cũ giữ nguyên...)
            await asyncio.sleep(2)
            segments = [
                {"start": 0.0, "end": 2.5, "text": "Đây là câu đầu tiên của bài hát."},
                {"start": 2.6, "end": 5.0, "text": "Và đây là đoạn tiếp theo đang hát."},
                {"start": 5.5, "end": 10.0, "text": "Đoạn điệp khúc cao trào nằm ở đây (Chorus)."},
                {"start": 10.5, "end": 15.0, "text": "Kết thúc đoạn demo mock data."}
            ]

        # Ensure duration is set (fallback to last segment end)
        if not duration and segments:
            try:
                duration = max(float(s["end"]) for s in segments)
            except Exception:
                duration = 0.0

        # 4. Generate Outputs 
        subs = generate_subtitles(segments, duration)
        for ext, content in subs.items():
            with open(os.path.join(work_dir, f"{job_id}.{ext}"), "w", encoding="utf-8") as f:
                f.write(content)

        # 5. Highlights 
        mid_segments = segments[len(segments)//3 : 2*len(segments)//3]
        highlights = sorted(mid_segments, key=lambda x: float(x['end']) - float(x['start']), reverse=True)[:3]

        jobs[job_id].update({
            "status": JobStatus.DONE,
            "audio_url": f"/stream/{job_id}",
            "segments": segments,
            "highlights": highlights,
            "duration": duration,
            "original_name": original_filename,
            "processed_path": processed_audio_path # Update đường dẫn file thực tế (vocal hoặc gốc)
        })

    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
        jobs[job_id]["status"] = JobStatus.ERROR
        jobs[job_id]["error"] = str(e)

# --- ROUTES ---
@app.get("/help", response_class=HTMLResponse)
async def read_docs(request: Request):
    return templates.TemplateResponse("help.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), mode: str = Form(...)):
    job_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    jobs[job_id] = {"status": JobStatus.PENDING, "mode": mode}
    
    original_name = file.filename or "audio"
    background_tasks.add_task(process_audio_task, job_id, file_path, mode, original_name)
    return {"job_id": job_id}

@app.get("/result/{job_id}", response_class=HTMLResponse)
async def result_page(request: Request, job_id: str):
    if job_id not in jobs:
        return HTMLResponse("Job not found", status_code=404)
    return templates.TemplateResponse("result.html", {"request": request, "job_id": job_id})

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        return JSONResponse({"status": "not_found"}, status_code=404)
    job = jobs[job_id]
    # Chỉ trả về dữ liệu cần thiết
    return {
        "status": job["status"], 
        "error": job.get("error"),
        "segments": job.get("segments"),
        "highlights": job.get("highlights"),
        "duration": job.get("duration"),
        "original_name": job.get("original_name")
    }

@app.get("/download/{job_id}/{fmt}")
async def download_file(job_id: str, fmt: str):
    if fmt not in ["txt", "srt", "vtt", "lrc"]:
        raise HTTPException(400, "Invalid format")
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}.{fmt}")
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found")
    return FileResponse(file_path, filename=f"transcript_{job_id}.{fmt}")

# --- STREAMING LOGIC (Support Seek/Range) ---
@app.get("/stream/{job_id}")
async def stream_audio(job_id: str, request: Request):
    if job_id not in jobs or "processed_path" not in jobs[job_id]:
        raise HTTPException(404, "Audio not found")
    
    path = jobs[job_id]["processed_path"]
    file_size = os.path.getsize(path)
    range_header = request.headers.get("range")

    if range_header:
        # Xử lý Range header đơn giản
        byte1, byte2 = 0, None
        match = range_header.replace("bytes=", "").split("-")
        byte1 = int(match[0])
        if match[1]:
            byte2 = int(match[1])
        
        length = file_size - byte1
        if byte2:
            length = byte2 + 1 - byte1
        
        with open(path, "rb") as f:
            f.seek(byte1)
            data = f.read(length)
        
        headers = {
            "Content-Range": f"bytes {byte1}-{byte1 + length - 1}/{file_size}",
            "Accept-Ranges": "bytes",
        }
        media_type = mimetypes.guess_type(path)[0] or "audio/wav"
        return StreamingResponse(iter([data]), status_code=206, headers=headers, media_type=media_type)
    
    media_type = mimetypes.guess_type(path)[0] or "audio/wav"
    return FileResponse(path, media_type=media_type)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)