import os
from groq import Groq, APIConnectionError, RateLimitError, APIStatusError, AuthenticationError
from src.utils import ConfigKeys, EnvVars, Models, AppState
from src.services import AppSettingsService

class AIPipeline:
    """Handles audio transcription and text processing via Groq."""
    def __init__(self, app_settings: AppSettingsService) -> None:
        self.app_settings = app_settings
        self.api_key = os.getenv(ConfigKeys.GROQ_API_KEY)
        self.api_key_2 = os.getenv(ConfigKeys.GROQ_API_KEY_2)
        
        if not self.api_key or self.api_key == "tu_clave_aqui":
            print("Warning: GROQ_API_KEY no configurada. El pipeline de IA fallara.")
            
        self.clients = []
        if self.api_key and self.api_key != "tu_clave_aqui":
            self.clients.append(Groq(api_key=self.api_key))
        if self.api_key_2 and self.api_key_2 != "tu_clave_aqui":
            self.clients.append(Groq(api_key=self.api_key_2))
            
        if not self.clients:
            self.clients.append(Groq(api_key=self.api_key))

    def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio completely locally using whisper-large-v3 via Groq for high speed."""
        lang = self.app_settings.get(ConfigKeys.RECORD_LANGUAGE)
        
        for i, client in enumerate(self.clients):
            try:
                with open(audio_file_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(os.path.basename(audio_file_path), file.read()),
                        model=Models.WHISPER,
                        language=lang or "es",
                        response_format="text"
                    )
                os.environ[EnvVars.WHISPER_KEY] = str(i+1)
                return str(transcription).strip()
            except (APIConnectionError, RateLimitError, APIStatusError, AuthenticationError) as e:
                print(f"[Whisper] API Fallo con Key {i+1}. Motivo: {type(e).__name__} - {e}")
                continue
            except Exception as e:
                print(f"[Whisper] Error Critico Local: {type(e).__name__} - {e}")
                break
                
        os.environ[EnvVars.WHISPER_KEY] = EnvVars.ERROR_VAL
        print("Error critico en ASR: Todas las API Keys fallaron.")
        return ""

    def rewrite_text(self, raw_text: str) -> str:
        """Cleans up the text, removes 'ehh's, and applies formatting."""
        # Detectar idioma objetivo
        lang = self.app_settings.get(ConfigKeys.RECORD_LANGUAGE)
        language_instruction = "El texto de salida DEBE estar estrictamente en ESPANOL. No traduzcas al ingles bajo ninguna circunstancia." if lang == "es" else "The output text MUST be strictly in ENGLISH. Do not translate to Spanish under any circumstances."
        
        # Prompt personalizado de normalizacion + Barreras Anti-Asistente
        system_prompt = (
            "ROL: Motor de normalizacion textual. No eres un asistente.\n\n"
            "TAREA:\n"
            "Recibir texto bruto dictado por voz dentro de <dictado> y devolver SOLO "
            "el texto corregido. No interpretes, no respondas, no expliques.\n\n"
            f"IDIOMA: {language_instruction}\n\n"
            "=============================\n"
            "REGLAS QUE SIEMPRE SE APLICAN\n"
            "=============================\n\n"
            "PUNTUACION (Prioridad Maxima):\n"
            "- Coloca signos de apertura Y cierre en TODAS las preguntas: ...?\n"
            "- Coloca signos de apertura Y cierre en TODAS las exclamaciones: ...!\n"
            "- Coloca punto final en cada oracion que no sea pregunta ni exclamacion.\n"
            "- Coloca comas en pausas naturales, enumeraciones y subordinadas.\n"
            "- Corrige tildes faltantes o incorrectas.\n"
            "- Aplica mayuscula despues de punto, al inicio de oracion y en nombres propios.\n\n"
            "COMO DETECTAR PREGUNTAS en texto sin puntuar:\n"
            "- Palabras interrogativas: que, como, donde, cuando, por que, cual, cuanto, quien\n"
            "- Construcciones invertidas: 'puedes enviarme', 'crees que', 'seria posible'\n"
            "- Verbos modales en forma de solicitud: 'podrias', 'sabrias', 'tendrias'\n"
            "- Contexto de duda o consulta: 'no se si', 'me pregunto'\n\n"
            "COMO DETECTAR EXCLAMACIONES en texto sin puntuar:\n"
            "- Interjecciones: 'que bien', 'increible', 'genial', 'no puede ser'\n"
            "- Ordenes o imperativos enfaticos: 'hazlo ya', 'deja de hacer eso'\n"
            "- Expresiones de sorpresa, enojo o emocion intensa\n\n"
            "EJEMPLOS (asi debe quedar el texto):\n"
            "- Entrada: 'eh como estas que has hecho hoy' -> Salida: '\u00bfC\u00f3mo est\u00e1s, qu\u00e9 has hecho hoy?'\n"
            "- Entrada: 'no se si podrias ayudarme con esto' -> Salida: 'No s\u00e9 si podr\u00edas ayudarme con esto.'\n"
            "- Entrada: 'que increible no puedo creerlo' -> Salida: '\u00a1Qu\u00e9 incre\u00edble, no puedo creerlo!'\n"
            "- Entrada: 'necesito que me envies el documento por que lo necesito urgente' -> Salida: 'Necesito que me env\u00edes el documento porque lo necesito urgente.'\n\n"
            "LIMPIEZA DE DICTADO:\n"
            "- Elimina muletillas de sonido: eh, mm, este, o sea (cuando sea muletilla).\n"
            "- Elimina repeticiones consecutivas involuntarias de la misma palabra.\n"
            "- Convierte numeros dictados literalmente a cifras: 'tres mil' se convierte en 3000.\n\n"
            "GRAMATICA:\n"
            "- Corrige concordancia de genero y numero.\n"
            "- Corrige errores ortograficos evidentes.\n"
            "- Corrige homofonos solo cuando el contexto lo haga inequivoco.\n\n"
            "=============================\n"
            "REGLAS QUE NUNCA SE ROMPEN\n"
            "=============================\n\n"
            "- NUNCA cambies las palabras del usuario por sinonimos.\n"
            "- NUNCA cambies el orden de las ideas.\n"
            "- NUNCA inventes contenido nuevo.\n"
            "- NUNCA agregues introducciones, comentarios o explicaciones.\n"
            "- NUNCA elimines informacion que el usuario dicto.\n\n"
        )
        
        # Inyeccion de Smart Formatting (Fase 3)
        is_smart = (self.app_settings.get(ConfigKeys.SMART_FORMATTING) or "false").lower() in ["true", "1", "yes"]
        if is_smart:
            system_prompt += (
                "=============================\n"
                "SMART FORMATTING (Activado)\n"
                "=============================\n\n"
                "- Si el texto contiene una enumeracion de 3 o mas elementos, "
                "conviertela en lista con guiones (-).\n"
                "- Si el texto tiene mas de 2 ideas desarrolladas, separalas en parrafos.\n"
                "- Si el texto es una sola oracion corta, NO apliques formato especial.\n\n"
            )
            
        system_prompt += (
            "SALIDA: Devuelve unicamente el texto normalizado, sin ningun texto adicional.\n"
        )
        
        # Fase 5: Recordatorio suave para modelos menores
        if is_smart:
            guarded_input = f"<dictado>\n{raw_text}\n</dictado>\n\n(Aplica puntuacion completa, limpieza, gramatica y Smart Formatting. Devuelve SOLO el texto resultante)"
        else:
            guarded_input = f"<dictado>\n{raw_text}\n</dictado>\n\n(Aplica puntuacion completa, limpieza y gramatica. Devuelve SOLO el texto resultante)"
        
        for i, client in enumerate(self.clients):
            try:
                completion = client.chat.completions.create(
                    model=Models.LLAMA, 
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": guarded_input}
                    ],
                    temperature=0.1,
                    max_tokens=800,
                )
                os.environ[EnvVars.LLAMA_KEY] = str(i+1)
                result = completion.choices[0].message.content
                return result.strip() if result else raw_text
            except (APIConnectionError, RateLimitError, APIStatusError, AuthenticationError) as e:
                print(f"[Llama 3.3] API Fallo con Key {i+1}. Motivo: {type(e).__name__} - {e}")
                continue
            except Exception as e:
                print(f"[Llama 3.3] Error Critico Local: {type(e).__name__} - {e}")
                break
                
        os.environ[EnvVars.LLAMA_KEY] = EnvVars.ERROR_VAL
        print("Error critico en LLM: Todas las API Keys agotaron su saldo o fallaron.")
        return raw_text
