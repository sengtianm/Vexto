import sys
sys.path.append('c:\\Proyectos\\Vexto')
from src.audio.capture import AudioRecorder
import time

mics = AudioRecorder.get_microphones()
print("Micrófonos detectados:")
for m in mics:
    print(m)

rec = AudioRecorder(device_index=1)
print("\nIntentando grabar con dispositivo ID 1...")
rec.start()
time.sleep(2)
wav = rec.stop()
print("WAV Path Obtenido:", wav)

import os
if wav and os.path.exists(wav):
    print("Éxito. WAV Tamaño:", os.path.getsize(wav))
    from src.llm.provider import AIPipeline
    pipe = AIPipeline()
    t = pipe.transcribe_audio(wav)
    print("Trans:", t)
else:
    print("FRACASO: El archivo WAV no se generó o el path es nulo.")
