import os
from groq import Groq
from dotenv import load_dotenv

def main():
    load_dotenv()
    client = Groq()
    try:
        models = client.models.list()
        print("Modelos disponibles en Groq:")
        for m in models.data:
            print("-", m.id)
            
        print("\nProbando generacion con 'openai/gpt-oss-20b'...")
        res = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": "Hola"}]
        )
        print("Gen exito:", res.choices[0].message.content)
    except Exception as e:
        print("Fallo listando o generando:", e)

if __name__ == '__main__':
    main()
