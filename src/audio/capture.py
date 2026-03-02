import sounddevice as sd
import numpy as np
import soundfile as sf
import queue
import tempfile
import os

class AudioRecorder:
    """Records audio from a specific microphone and saves it to a temp WAV file."""
    
    @staticmethod
    def get_microphones():
        """Returns a list of dicts with 'id' and 'name' for available input devices."""
        try:
            devices = sd.query_devices()
            mics = []
            hostapi_default = sd.default.hostapi
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0 and dev['hostapi'] == hostapi_default:
                    mics.append({"id": i, "name": dev['name']})
            return mics
        except Exception as e:
            print(f"Error querying mics: {e}")
            return []

    def __init__(self, samplerate=16000, channels=1, device_index=None):
        self.samplerate = samplerate
        self.channels = channels
        self.device_index = device_index
        self.q = queue.Queue()
        self.is_recording = False
        self.current_volume = 0.0

        self._stream = None

    def _callback(self, indata, frames, time, status):
        """Called continuously. Only saves data if we are actively recording."""
        if status:
            pass # Silently ignore status to avoid spamming the console
            
        # Calcular volumen siempre (para la UI futura si se requiere, o descartar)
        rms = np.sqrt(np.mean(indata**2))
        self.current_volume = min(1.0, rms * 15)
        
        # SI Vexto está "Escuchando", guardamos el audio. Si no, lo descartamos al vacío (0 latencia).
        if self.is_recording:
            self.q.put(indata.copy())

    def start(self):
        """Simply flips the recording switch to True."""
        if self.is_recording: return
        
        # Clear any leftover data in the queue
        while not self.q.empty(): 
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
                
        self.is_recording = True
        
        if self._stream is None:
            # Si el device_index es invalido, sounddevice usará el sistema por defecto
            self._stream = sd.InputStream(
                samplerate=self.samplerate, 
                channels=self.channels, 
                device=self.device_index,
                callback=self._callback
            )
            self._stream.start()

    def stop(self):
        """Stops saving audio and returns the path to the saved WAV file. Returns None if no audio."""
        if not self.is_recording: return None
        self.is_recording = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        if self.q.empty():
            return None

        
        # Collect all audio frames from the queue
        audio_data = []
        while not self.q.empty():
            audio_data.append(self.q.get())
            
        if not audio_data:
            return None
            
        # Concatenate into a single numpy array
        audio_np = np.concatenate(audio_data, axis=0)
        
        # Create a temporary file
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        # Write to WAV format
        sf.write(temp_path, audio_np, self.samplerate)
        
        return temp_path
