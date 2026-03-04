import sys
sys.path.append('c:\\Proyectos\\Vexto')
from src.llm.provider import AIPipeline
import logging

logging.basicConfig(level=logging.ERROR)

def main():
    p = AIPipeline()
    text = "Listo, pues mientras tanto continuamos con el plan de implementación de mejora de auditoría de arquitectónica y deuda técnica. Mi pregunta es, ¿ya hiciste todo el nivel rojo? Porque ya estábamos en el punto 1, o sea que ya hiciste el punto 2 y el punto 3 del nivel rojo. Solo confírmame y no implementes nada."
    print("Enviando al LLM...")
    res = p.rewrite_text(text)
    print("Resultado Rewrite:", repr(res))

if __name__ == '__main__':
    main()
