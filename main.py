import os
import librosa
import paho.mqtt.client as mqtt
import json
import uuid
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse

app = FastAPI()


MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")

@app.get("/", response_class=HTMLResponse)
async def home():
    """Sirve la interfaz web al usuario"""
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "Archivo index.html no encontrado en el servidor."

@app.post("/analizar")
async def analizar_beats(file: UploadFile = File(...)):
    """Procesa el MP3 y envía los timestamps de los beats"""
 
    file_id = str(uuid.uuid4())
    file_location = f"temp_{file_id}.mp3"
    
    try:
       
        content = await file.read()
        with open(file_location, "wb") as f:
            f.write(content)
        
     
        y, sr = librosa.load(file_location, sr=None)
        
 
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        peaks = librosa.util.peak_pick(
            onset_env, 
            pre_max=3, post_max=3, pre_avg=3, post_avg=5, 
            delta=0.5, wait=10
        )
        
        beat_times = librosa.frames_to_time(peaks, sr=sr).tolist()
        
    
        payload = json.dumps({
            "nombre_archivo": file.filename,
            "total_beats": len(beat_times),
            "beats": [round(b, 3) for b in beat_times]
        })

    
        client = mqtt.Client()
        client.username_pw_set(MQTT_USER, MQTT_PASS)
        client.tls_set() # Render requiere TLS para conectar a brokers en la nube
        client.connect(MQTT_HOST, 8883)
        client.publish("musica/beats", payload, qos=1)
        client.disconnect()

        return {
            "status": "Sincronizado",
            "info": f"Se enviaron {len(beat_times)} beats a la Raspberry Pi."
        }

    except Exception as e:
        return {"status": "Error", "detalle": str(e)}
    
    finally:
        # Limpieza técnica: Borrar el MP3 para no agotar el almacenamiento de Render
        if os.path.exists(file_location):

            os.remove(file_location)
