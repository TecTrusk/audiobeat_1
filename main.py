import os
import librosa
import uuid
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/analizar")
async def analizar_y_descargar(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    audio_path = f"temp_{file_id}.mp3"
    txt_path = f"tiempos_{file_id}.txt"
    
    try:
        # 1. Guardar MP3 temporal
        content = await file.read()
        with open(audio_path, "wb") as f:
            f.write(content)
        
        # 2. Procesar con Librosa
        # Por esta (fuerza la conversión a mono):
        y, sr = librosa.load(audio_path, sr=None, mono=True)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        peaks = librosa.util.peak_pick(onset_env, pre_max=3, post_max=3, pre_avg=3, post_avg=5, delta=0.5, wait=10)
        beat_times = librosa.frames_to_time(peaks, sr=sr)
        
        # 3. Crear el archivo TXT con los tiempos
        with open(txt_path, "w") as f:
            for t in beat_times:
                f.write(f"{round(t, 3)}\n")
        
        # 4. Retornar el archivo para descarga automática
        return FileResponse(
            path=txt_path, 
            filename="tiempos_beat.txt", 
            media_type='text/plain'
        )

    except Exception as e:
        print(f"ERROR CRÍTICO: {str(e)}") # Esto hará que aparezca en los LOGS de Render
        return {"error": str(e)}
    finally:
        # Limpieza de archivos temporales después de la respuesta
        if os.path.exists(audio_path): os.remove(audio_path)
        # Nota: El TXT se borra idealmente con un BackgroundTask, 
        # pero para esta prueba lo dejaremos así.


