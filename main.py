from fastapi import FastAPI
import requests
import re

app = FastAPI(
    title="API Windguru Garopaba",
    version="3.0.0"
)

WINDGURU_URL = "https://old.windguru.cz/zht/index.php?sc=209196"


@app.get("/")
def inicio():
    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": 209196,
        "versao": "3.0"
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

        # Mantém o texto da página
        texto = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
        texto = re.sub(r"<style.*?</style>", " ", texto, flags=re.S)
        texto = re.sub(r"<[^>]+>", " ", texto)
        texto = re.sub(r"\s+", " ", texto)

        # Procura algumas linhas importantes
        ondas = encontrar_linha(texto, "波浪")
        swell = encontrar_linha(texto, "湧浪")
        vento = encontrar_linha(texto, "風速")
        rajada = encontrar_linha(texto, "陣風")

        return {
            "local": "Garopaba",
            "windguru_spot": 209196,
            "status": "dados_extraidos",
            "tamanho_pagina": len(html),

            "teste": {
                "ondas": ondas,
                "swell": swell,
                "vento": vento,
                "rajada": rajada
            }
        }

    except Exception as erro:

        return {
            "local": "Garopaba",
            "windguru_spot": 209196,
            "status": "erro",
            "erro": str(erro)
        }


def encontrar_linha(texto, termo):

    posicao = texto.find(termo)

    if posicao == -1:
        return "nao encontrado"

    # Pega um trecho depois do nome da linha
    trecho = texto[posicao:posicao + 1000]

    return trecho
