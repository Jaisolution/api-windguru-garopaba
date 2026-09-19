from fastapi import FastAPI
import requests
import re
from html import unescape

app = FastAPI()

URL = "https://old.windguru.cz/zht/index.php?sc=209196"


@app.get("/")
def teste():

    try:
        resposta = requests.get(
            URL,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/120.0 Safari/537.36"
                )
            },
            timeout=30
        )

        resposta.raise_for_status()

        html = resposta.text
        texto = unescape(html)

        # Retira tags
        texto_limpo = re.sub(r"<[^>]+>", " ", texto)
        texto_limpo = re.sub(r"\s+", " ", texto_limpo)

        resultados = []

        # Procura TODAS as temperaturas escritas como °C
        padrao = re.compile(
            r'(-?\d{1,2}(?:[.,]\d+)?)\s*°\s*C',
            re.IGNORECASE
        )

        for encontrado in padrao.finditer(texto_limpo):

            temperatura = encontrado.group(1)

            inicio = max(0, encontrado.start() - 150)
            fim = min(
                len(texto_limpo),
                encontrado.end() + 150
            )

            contexto = texto_limpo[inicio:fim]

            resultados.append({
                "temperatura": temperatura,
                "contexto": contexto
            })

        return {
            "status": "ok",
            "quantidade": len(resultados),
            "resultados": resultados
        }

    except Exception as erro:

        return {
            "status": "erro",
            "erro": str(erro)
        }
