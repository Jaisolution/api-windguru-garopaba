from fastapi import FastAPI
import requests
import re

app = FastAPI(
    title="API Windguru Garopaba",
    version="5.0.0"
)

WINDGURU_URL = "https://old.windguru.cz/zht/index.php?sc=209196"


@app.get("/")
def inicio():
    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": 209196,
        "versao": "5.0"
    }


@app.get("/garopaba")
def garopaba():

    try:

        resposta = requests.get(
            WINDGURU_URL,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=30
        )

        html = resposta.text

        # Procuramos palavras que aparecem
        # perto da tabela de previsão
        palavras = [
            "Windguru",
            "GFS",
            "Wave",
            "wave",
            "swell",
            "Swell",
            "wind",
            "Wind",
            "rain",
            "cloud",
            "temp"
        ]

        encontrados = {}

        for palavra in palavras:

            posicoes = []

            inicio = 0

            while True:

                pos = html.lower().find(
                    palavra.lower(),
                    inicio
                )

                if pos == -1:
                    break

                posicoes.append(pos)

                inicio = pos + len(palavra)

                if len(posicoes) >= 5:
                    break

            encontrados[palavra] = posicoes

        # Pega alguns trechos do HTML
        # onde encontramos GFS/Wave
        trechos = []

        for palavra in ["GFS", "Wave", "wave", "swell", "wind"]:

            pos = html.lower().find(palavra.lower())

            if pos != -1:

                trecho = html[
                    max(0, pos - 500):
                    min(len(html), pos + 2500)
                ]

                trechos.append({
                    "palavra": palavra,
                    "posicao": pos,
                    "html": trecho
                })

        return {
            "status": "ok",
            "tamanho_html": len(html),
            "encontrados": encontrados,
            "trechos": trechos
        }

    except Exception as erro:

        return {
            "status": "erro",
            "erro": str(erro)
        }
