from fastapi import FastAPI
import requests
import json
import re

app = FastAPI(
    title="API Windguru Garopaba",
    description="API de previsão para ESP32",
    version="9.0"
)

WINDGURU_URL = "https://old.windguru.cz/zht/index.php?sc=209196"

HORARIOS = ["06", "12", "18"]
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

    for encontrado in re.finditer(padrao, html):

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

            modelos[dados.get("model")] = previsao

        except Exception:
            continue

    return modelos


def valor(lista, indice):

    if not isinstance(lista, list):
        return None

    if indice >= len(lista):
        return None

    return lista[indice]


def numero(valor_recebido):

    if valor_recebido is None:
        return None

    try:
        return round(float(valor_recebido), 1)

    except Exception:
        return None


def no_para_kmh(valor_recebido):

    if valor_recebido is None:
        return None

    try:
        return round(float(valor_recebido) * 1.852, 1)

    except Exception:
        return None


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

    indice = int(
        (float(graus) + 11.25) / 22.5
    ) % 16

    return direcoes[indice]


def montar_dias(modelos):

    ondas = modelos.get("gfsw")
    tempo = modelos.get("gfs")

    if not ondas:
        return []

    if not tempo:
        return []

    horas_ondas = ondas.get("hours", [])
    horas_tempo = tempo.get("hours", [])

    dias = {}

    for i, hora in enumerate(horas_ondas):

        hora_wg = valor(
            ondas.get("hr_h"),
            i
        )

        dia_wg = valor(
            ondas.get("hr_d"),
            i
        )

        if hora_wg is None or dia_wg is None:
            continue

        hora_formatada = str(hora_wg).zfill(2)

        # Só queremos 06, 12 e 18
        if hora_formatada not in HORARIOS:
            continue

        # Procurar o mesmo horário no GFS
        indice_tempo = None

        for j, hora_tempo in enumerate(horas_tempo):

            if hora_tempo == hora:
                indice_tempo = j
                break

        if indice_tempo is None:
            continue

        chave_dia = str(dia_wg)

        if chave_dia not in dias:

            dias[chave_dia] = {
                "data": chave_dia,
                "horarios": {}
            }

        # =========================
        # ONDA
        # =========================

        onda = numero(
            valor(
                ondas.get("HTSGW"),
                i
            )
        )

        periodo = numero(
            valor(
                ondas.get("PERPW"),
                i
            )
        )

        direcao_onda = numero(
            valor(
                ondas.get("DIRPW"),
                i
            )
        )

        # =========================
        # SWELL
        # =========================

        swell = numero(
            valor(
                ondas.get("SWELL1"),
                i
            )
        )

        periodo_swell = numero(
            valor(
                ondas.get("SWPER1"),
                i
            )
        )

        direcao_swell = numero(
            valor(
                ondas.get("SWDIR1"),
                i
            )
        )

        # =========================
        # VENTO
        # =========================

        vento = no_para_kmh(
            valor(
                tempo.get("WINDSPD"),
                indice_tempo
            )
        )

        rajada = no_para_kmh(
            valor(
                tempo.get("GUST"),
                indice_tempo
            )
        )

        direcao_vento = numero(
            valor(
                tempo.get("WINDDIR"),
                indice_tempo
            )
        )

        # =========================
        # TEMPERATURA
        # =========================

        temperatura = numero(
            valor(
                tempo.get("TMP"),
                indice_tempo
            )
        )

        # =========================
        # NUVENS
        # =========================

        nuvens = numero(
            valor(
                tempo.get("TCDC"),
                indice_tempo
            )
        )

        if nuvens is None:
            nuvens = 0

        # =========================
        # CHUVA
        # =========================

        chuva = numero(
            valor(
                tempo.get("APCP"),
                indice_tempo
            )
        )

        if chuva is None:
            chuva = 0

        # =========================
        # DADOS DO HORÁRIO
        # =========================

        dados_horario = {

            "onda": onda,

            "periodo": periodo,

            "direcao": direcao_compass(
                direcao_onda
            ),

            "swell": swell,

            "periodo_swell": periodo_swell,

            "direcao_swell": direcao_compass(
                direcao_swell
            ),

            "vento": vento,

            "rajada": rajada,

            "vento_dir": direcao_compass(
                direcao_vento
            ),

            "temp": temperatura,

            "nuvens": nuvens,

            "chuva": chuva
        }

        # Nome do período
        if hora_formatada == "06":
            nome = "manha"

        elif hora_formatada == "12":
            nome = "tarde"

        else:
            nome = "noite"

        dias[chave_dia]["horarios"][nome] = dados_horario

    # =========================
    # CONVERTER PARA LISTA
    # =========================

    resultado = []

    for dia, dados in dias.items():

        item = {
            "data": dados["data"]
        }

        horarios = dados["horarios"]

        if "manha" in horarios:
            item["manha"] = horarios["manha"]

        if "tarde" in horarios:
            item["tarde"] = horarios["tarde"]

        if "noite" in horarios:
            item["noite"] = horarios["noite"]

        resultado.append(item)

    # Somente 4 dias
    return resultado[:MAX_DIAS]


@app.get("/")
def inicio():

    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": 209196,
        "versao": "9.0"
    }


@app.get("/garopaba")
def garopaba():

    try:

        html = baixar_windguru()

        modelos = extrair_modelos(html)

        dias = montar_dias(modelos)

        return {
            "status": "ok",
            "local": "Garopaba",
            "windguru_spot": 209196,
            "unidade_onda": "metros",
            "unidade_vento": "km/h",
            "dias": dias
        }

    except Exception as erro:

        return {
            "status": "erro",
            "erro": str(erro)
        }
