from fastapi import FastAPI
import requests
import re

app = FastAPI(
    title="API Windguru Garopaba",
    description="API de previsão para ESP32",
    version="4.0.0"
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


def limpar_html(html):

    html = re.sub(
        r"<script.*?</script>",
        " ",
        html,
        flags=re.S | re.I
    )

    html = re.sub(
        r"<style.*?</style>",
        " ",
        html,
        flags=re.S | re.I
    )

    html = re.sub(
        r"<[^>]+>",
        " ",
        html
    )

    html = html.replace("&nbsp;", " ")

    html = re.sub(
        r"\s+",
        " ",
        html
    )

    return html


def extrair_numeros(texto, inicio, fim=None):

    pos = texto.find(inicio)

    if pos == -1:
        return []

    if fim:
        fim_pos = texto.find(fim, pos)

        if fim_pos != -1:
            trecho = texto[pos:fim_pos]
        else:
            trecho = texto[pos:pos + 5000]

    else:
        trecho = texto[pos:pos + 5000]

    numeros = re.findall(
        r"(?<![\w.])-?\d+(?:\.\d+)?",
        trecho
    )

    return numeros


@app.get("/")
def inicio():

    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": 209196,
        "versao": "4.0"
    }


@app.get("/teste")
def teste():

    try:

        html = baixar_windguru()

        texto = limpar_html(html)

        return {
            "status": "ok",
            "tamanho_html": len(html),
            "tamanho_texto": len(texto),
            "tem_ondas": "波浪" in texto,
            "tem_swell": "湧浪" in texto,
            "tem_vento": "風速" in texto,
            "tem_rajada": "陣風" in texto,
            "tem_temperatura": "氣溫" in texto,
            "tem_chuva": "降雨" in texto,
            "tem_nuvens": "雲層覆蓋" in texto
        }

    except Exception as erro:

        return {
            "status": "erro",
            "erro": str(erro)
        }


@app.get("/garopaba")
def garopaba():

    try:

        html = baixar_windguru()

        texto = limpar_html(html)

        # ----------------------------------
        # ONDAS
        # ----------------------------------

        ondas = extrair_numeros(
            texto,
            "波浪 (m)",
            "*波浪週期"
        )

        # ----------------------------------
        # PERÍODO DAS ONDAS
        # ----------------------------------

        periodo = extrair_numeros(
            texto,
            "*波浪週期(秒)",
            "波浪向"
        )

        # ----------------------------------
        # SWELL
        # ----------------------------------

        swell = extrair_numeros(
            texto,
            "湧浪 (m)",
            "湧浪週期"
        )

        # ----------------------------------
        # PERÍODO DO SWELL
        # ----------------------------------

        periodo_swell = extrair_numeros(
            texto,
            "湧浪週期（秒）",
            "Swell energy"
        )

        # ----------------------------------
        # VENTO
        # ----------------------------------

        vento = extrair_numeros(
            texto,
            "風速 (節)",
            "陣風"
        )

        # ----------------------------------
        # RAJADA
        # ----------------------------------

        rajada = extrair_numeros(
            texto,
            "陣風 (節)",
            "風向"
        )

        # ----------------------------------
        # TEMPERATURA
        # ----------------------------------

        temperatura = extrair_numeros(
            texto,
            "*氣溫 (°C)",
            "雲層覆蓋"
        )

        # ----------------------------------
        # CHUVA
        # ----------------------------------

        chuva = extrair_numeros(
            texto,
            "*降雨 (mm/1時)",
            "Windguru 分數"
        )

        return {

            "local": "Garopaba",

            "windguru_spot": 209196,

            "status": "dados_extraidos",

            "modelo": "GFS-Wave 25 km",

            "dados": {

                "ondas_m": ondas,

                "periodo_onda_s": periodo,

                "swell_m": swell,

                "periodo_swell_s": periodo_swell,

                "vento_nos": vento,

                "rajada_nos": rajada,

                "temperatura_c": temperatura,

                "chuva_mm": chuva

            }

        }

    except Exception as erro:

        return {

            "local": "Garopaba",

            "windguru_spot": 209196,

            "status": "erro",

            "erro": str(erro)

        }
