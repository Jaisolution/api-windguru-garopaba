from fastapi import FastAPI
import requests
import json
import re
from datetime import datetime, timedelta, timezone

app = FastAPI(
    title="API Windguru Garopaba",
    description="API de previsão para ESP32",
    version="8.0"
)

WINDGURU_URL = "https://old.windguru.cz/zht/index.php?sc=209196"

MAX_DIAS = 4


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

    modelos = {}

    padrao = r'var\s+wg_fcst_tab_data_(\d+)\s*=\s*'

    encontrados = re.finditer(padrao, html)

    for encontrado in encontrados:

        try:

            inicio = encontrado.end()

            decoder = json.JSONDecoder()

            dados, tamanho = decoder.raw_decode(
                html[inicio:]
            )

            fcst = dados.get("fcst", {})

            id_model = str(dados.get("id_model"))

            if id_model in fcst:
                previsao = fcst[id_model]

            elif fcst:
                primeira_chave = list(fcst.keys())[0]
                previsao = fcst[primeira_chave]

            else:
                continue

            nome_modelo = dados.get("model")

            modelos[nome_modelo] = {
                "dados": dados,
                "previsao": previsao
            }

        except Exception:
            continue

    return modelos


def direcao_compass(graus):

    if graus is None:
        return None

    direcoes = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW"
    ]

    indice = int((float(graus) + 11.25) / 22.5) % 16

    return direcoes[indice]


def no_para_kmh(valor):

    if valor is None:
        return None

    return round(float(valor) * 1.852, 1)


def numero(valor):

    if valor is None:
        return None

    try:
        return round(float(valor), 2)

    except:
        return None


def obter_valor(lista, indice):

    if not isinstance(lista, list):
        return None

    if indice >= len(lista):
        return None

    return lista[indice]


def montar_previsao(modelos):

    onda = modelos.get("gfsw", {}).get("previsao", {})
    tempo = modelos.get("gfs", {}).get("previsao", {})

    if not onda:
        return []

    if not tempo:
        return []

    horas_onda = onda.get("hours", [])
    horas_tempo = tempo.get("hours", [])

    resultados = []

    for i, hora_onda in enumerate(horas_onda):

        # Procurar o mesmo horário no modelo GFS
        indice_tempo = None

        for j, hora_tempo in enumerate(horas_tempo):

            if hora_tempo == hora_onda:
                indice_tempo = j
                break

        if indice_tempo is None:
            continue

        dia = obter_valor(
            onda.get("hr_d"),
            i
        )

        hora = obter_valor(
            onda.get("hr_h"),
            i
        )

        if dia is None or hora is None:
            continue

        # =========================
        # ONDAS
        # =========================

        altura_onda = numero(
            obter_valor(
                onda.get("HTSGW"),
                i
            )
        )

        periodo_onda = numero(
            obter_valor(
                onda.get("PERPW"),
                i
            )
        )

        direcao_onda = numero(
            obter_valor(
                onda.get("DIRPW"),
                i
            )
        )

        # =========================
        # SWELL
        # =========================

        altura_swell = numero(
            obter_valor(
                onda.get("SWELL1"),
                i
            )
        )

        periodo_swell = numero(
            obter_valor(
                onda.get("SWPER1"),
                i
            )
        )

        direcao_swell = numero(
            obter_valor(
                onda.get("SWDIR1"),
                i
            )
        )

        # =========================
        # VENTO
        # =========================

        vento = no_para_kmh(
            obter_valor(
                tempo.get("WINDSPD"),
                indice_tempo
            )
        )

        rajada = no_para_kmh(
            obter_valor(
                tempo.get("GUST"),
                indice_tempo
            )
        )

        direcao_vento = numero(
            obter_valor(
                tempo.get("WINDDIR"),
                indice_tempo
            )
        )

        # =========================
        # TEMPERATURA
        # =========================

        temperatura = numero(
            obter_valor(
                tempo.get("TMP"),
                indice_tempo
            )
        )

        # =========================
        # NUVENS
        # =========================

        nuvens = numero(
            obter_valor(
                tempo.get("TCDC"),
                indice_tempo
            )
        )

        # =========================
        # CHUVA
        # =========================

        chuva = numero(
            obter_valor(
                tempo.get("APCP"),
                indice_tempo
            )
        )

        if chuva is None:
            chuva = 0

        # =========================
        # RESULTADO
        # =========================

        item = {
            "dia": str(dia),
            "hora": str(hora) + ":00",

            "onda": altura_onda,
            "periodo": periodo_onda,
            "direcao_onda": direcao_onda,
            "direcao_onda_nome": direcao_compass(
                direcao_onda
            ),

            "swell": altura_swell,
            "periodo_swell": periodo_swell,
            "direcao_swell": direcao_swell,
            "direcao_swell_nome": direcao_compass(
                direcao_swell
            ),

            "vento": vento,
            "rajada": rajada,
            "direcao_vento": direcao_vento,
            "direcao_vento_nome": direcao_compass(
                direcao_vento
            ),

            "temperatura": temperatura,
            "nuvens": nuvens,
            "chuva": chuva
        }

        resultados.append(item)

    return resultados


@app.get("/")
def inicio():

    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": 209196,
        "versao": "8.0"
    }


@app.get("/garopaba")
def garopaba():

    try:

        html = baixar_windguru()

        modelos = extrair_modelos(html)

        previsao = montar_previsao(
            modelos
        )

        return {
            "status": "ok",
            "local": "Garopaba",
            "windguru_spot": 209196,
            "unidade_onda": "metros",
            "unidade_vento": "km/h",
            "previsao": previsao
        }

    except Exception as erro:

        return {
            "status": "erro",
            "erro": str(erro)
        }
