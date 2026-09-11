from fastapi import FastAPI
import requests
import re

app = FastAPI(
    title="API Windguru Garopaba",
    description="API de previsão para ESP32",
    version="2.0.0"
)

WINDGURU_URL = "https://old.windguru.cz/zht/index.php?sc=209196"


@app.get("/")
def inicio():
    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": 209196,
        "versao": "2.0"
    }


@app.get("/garopaba")
def garopaba():

    try:
        resposta = requests.get(
            WINDGURU_URL,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=20
        )

        texto = resposta.text

        # Converte o HTML em texto simples
        texto = re.sub(r"<[^>]+>", " ", texto)
        texto = re.sub(r"\s+", " ", texto)

        return {
            "local": "Garopaba",
            "windguru_spot": 209196,
            "status": "dados_recebidos",
            "tamanho_pagina": len(texto),
            "mensagem": "Windguru acessado com sucesso"
        }

    except Exception as erro:

        return {
            "local": "Garopaba",
            "windguru_spot": 209196,
            "status": "erro",
            "erro": str(erro)
        }
