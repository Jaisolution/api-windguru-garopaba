from fastapi import FastAPI
import requests
import re

app = FastAPI()

URL = "https://old.windguru.cz/zht/index.php?sc=209196"


def baixar():
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
    return resposta.text


@app.get("/")
def inicio():

    try:
        html = baixar()

        return {
            "status": "online",
            "teste": "temperatura agua",
            "tamanho_html": len(html)
        }

    except Exception as erro:
        return {
            "status": "erro",
            "erro": str(erro)
        }


@app.get("/teste")
def teste():

    try:
        html = baixar()

        resultados = []

        # Procura ocorrencias do numero 16 no HTML BRUTO.
        # Nao remove tags nem JavaScript.
        for encontrado in re.finditer(
            r'(?<!\d)16(?:[.,]0)?(?!\d)',
            html
        ):

            inicio = max(
                0,
                encontrado.start() - 300
            )

            fim = min(
                len(html),
                encontrado.end() + 300
            )

            contexto = html[inicio:fim]

            resultados.append({
                "posicao": encontrado.start(),
                "contexto": contexto
            })

            # Evita uma resposta gigantesca
            if len(resultados) >= 30:
                break

        return {
            "status": "ok",
            "tamanho_html": len(html),
            "quantidade_mostrada": len(resultados),
            "resultados": resultados
        }

    except Exception as erro:

        return {
            "status": "erro",
            "erro": str(erro)
        }
