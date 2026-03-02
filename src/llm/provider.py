import os
from groq import Groq
from dotenv import load_dotenv

class AIPipeline:
    """Handles audio transcription and text processing via Groq."""
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        
        if not self.api_key or self.api_key == "tu_clave_aqui":
            print("Warning: GROQ_API_KEY no configurada. El pipeline de IA fallará.")
            
        self.client = Groq(api_key=self.api_key)

    def transcribe_audio(self, audio_file_path):
        """Transcribe audio completely locally using whisper-large-v3 via Groq for high speed."""
        try:
            with open(audio_file_path, "rb") as file:
                # Opcional: Especificar idioma
                lang = os.getenv("RECORD_LANGUAGE", "es")
                transcription = self.client.audio.transcriptions.create(
                    file=(os.path.basename(audio_file_path), file.read()),
                    model="whisper-large-v3",
                    language=lang,
                    response_format="text"
                )
            return transcription.strip()
        except Exception as e:
            print(f"Error en ASR: {e}")
            return ""

    def rewrite_text(self, raw_text):
        """Cleans up the text, removes 'ehh's, and applies formatting."""
        # Detectar idioma objetivo
        lang = os.getenv("RECORD_LANGUAGE", "es")
        language_instruction = "El texto de salida DEBE estar estrictamente en ESPAÑOL. No traduzcas al inglés bajo ninguna circunstancia." if lang == "es" else "The output text MUST be strictly in ENGLISH. Do not translate to Spanish under any circumstances."
        
        # Prompt personalizado de normalización provisto por el usuario
        system_prompt = (
            "Eres un motor de normalización textual.\n\n"
            "Tu única tarea es ajustar el texto del usuario a un formato formal básico, "
            "similar al modo 'Formal' de una herramienta de dictado.\n\n"
            "Objetivo:\n"
            "Corregir forma, no contenido.\n\n"
            f"Regla de Idioma (CRÍTICA): {language_instruction}\n\n"
            "Reglas obligatorias:\n"
            "1. Corrige capitalización.\n"
            "2. Corrige puntuación.\n"
            "3. Añade signos de apertura de interrogación y exclamación cuando falten (si aplica al idioma).\n"
            "4. Añade tildes cuando sean necesarias (si aplica al idioma).\n"
            "5. Corrige errores gramaticales evidentes (por ejemplo, preposiciones incorrectas o concordancia básica).\n"
            "6. Mantén exactamente las mismas palabras siempre que sea posible.\n"
            "7. No sustituyas vocabulario informal por vocabulario más profesional.\n"
            "8. No eleves el registro.\n"
            "9. No reformules ideas.\n"
            "10. No agregues saludos, despedidas ni estructura de correo.\n"
            "11. No amplíes ni reduzcas el contenido.\n"
            "12. No cambies el tono conversacional.\n"
            "13. Puedes añadir comas que reflejen pausas naturales del habla.\n"
            "14. Puedes dividir oraciones si mejora la claridad.\n"
            "15. Puedes realizar microajustes naturales en expresiones habladas si no cambian el significado (ejemplo: separar palabras compuestas coloquiales).\n"
            "16. No elimines muletillas si forman parte del tono original.\n"
            "17. No expliques nada.\n\n"
            "No debe parecer un correo corporativo ni un comunicado formal.\n\n"
        )
        
        # Inyección de Smart Formatting (Fase 3)
        if os.getenv("SMART_FORMATTING", "False").lower() in ["true", "1", "yes"]:
            system_prompt += (
                "---- REGLAS ADICIONALES DE FORMATEO (SMART FORMATTING ACTIVO) ----\n"
                "Aplica formato estructurado (Markdown) de manera muy agresiva e inteligente si la entrada lo amerita:\n"
                "- Si el usuario enlista o enumera cosas (Ej: 'compra leche huevos pan'), sepáralas forzosamente usando viñetas (guiones -) y saltos de línea reales.\n"
                "- Si el usuario dicta un texto muy largo con diversos temas, rómpelo dinámicamente en párrafos distintos separados por doble salto de línea.\n"
                "- Sé proactivo y asume cuándo el hablante quería crear una lista o un bloque de texto ordenado, y devuélvelo hermoso y legible.\n\n"
            )
            
        system_prompt += (
            "Salida:\n"
            "Devuelve únicamente el texto ajustado (y formateado si aplica), sin introducciones."
        )
        
        try:
            completion = self.client.chat.completions.create(
                # Usamos Llama 3.3 70B según tu petición para mayor calidad de redacción
                model="llama-3.3-70b-versatile", 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_text}
                ],
                temperature=0.3,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error en LLM: {e}")
            return raw_text
