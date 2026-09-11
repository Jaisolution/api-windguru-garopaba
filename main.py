from fastapi import FastAPI
import requests
import json
import re

app = FastAPI(
    title="API Windguru Garopaba",
    description="API de previsão para ESP32",
    version="6.0.0"
)

WINDGURU_URL = "https://old.windguru.cz/zht/index.php?sc=209196"


def baixar_windguru():

    resposta = requests.get(
        WINDGURU_URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    resposta.raise_for_status()

    return resposta.text


def extrair_modelos(html):

    modelos = []

    padrao = r'var\s+wg_fcst_tab_data_(\d+)\s*=\s*'

    encontrados = re.finditer(padrao, html)

    for encontrado in encontrados:

        numero = encontrado.group(1)

        inicio = encontrado.end()

        try:

            decoder = json.JSONDecoder()

            dados, tamanho = decoder.raw_decode(
                html[inicio:]
            )

            modelos.append({
                "id": numero,
                "spot": dados.get("spot"),
                "modelo": dados.get("model"),
                "id_model": dados.get("id_model"),
                "latitude": dados.get("lat"),
                "longitude": dados.get("lon"),
                "variaveis": list(
                    dados.get("fcst", {}).get(
                        str(dados.get("id_model")),
                        {}
                    ).keys()
                )
            })

        except Exception as erro:

            modelos.append({
                "id": numero,
                "erro": str(erro)
            })

    return modelos


@app.get("/")
def inicio():

    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": 209196,
        "versao": "6.0"
    }


@app.get("/garopaba")
def garopaba():

    try:

        html = baixar_windguru()

        modelos = extrair_modelos(html)

        return {
            "status": "ok",
            "local": "Garopaba",
            "windguru_spot": 209196,
            "tamanho_html": len(html),
            "modelos": modelos
        }

    except Exception as erro:

        return {
            "status": "erro",
            "erro": str(erro)
        }
