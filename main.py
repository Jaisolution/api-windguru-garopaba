from fastapi import FastAPI
import requests
import re
import json
from datetime import datetime
from zoneinfo import ZoneInfo

app = FastAPI()

SPOT = 209196
WINDGURU_URL = f"https://old.windguru.cz/int/iapi.php?sc={SPOT}"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def direcao_graus(graus):
    if graus is None:
        return ""

    try:
        g = float(graus) % 360
    except:
        return ""

    direcoes = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW"
    ]

    indice = int((g + 11.25) / 22.5) % 16
    return direcoes[indice]


def kmh(valor):
    if valor is None:
        return None

    try:
        return round(float(valor) * 1.852, 1)
    except:
        return None


def numero(valor):
    if valor is None:
        return None

    try:
        return float(valor)
    except:
        return None


def extrair_variavel(texto, nome):
    """
    Procura uma variável JavaScript do Windguru.
    """

    padroes = [
        rf'{nome}\s*=\s*(\[[\s\S]*?\]);',
        rf'var\s+{nome}\s*=\s*(\[[\s\S]*?\]);',
        rf'window\.{nome}\s*=\s*(\[[\s\S]*?\]);'
    ]

    for padrao in padroes:
        m = re.search(padrao, texto)

        if m:
            try:
                return json.loads(m.group(1))
            except:
                pass

    return None


def buscar_windguru():

    url = f"https://old.windguru.cz/ee/index.php?sc={SPOT}"

    r = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    r.raise_for_status()

    texto = r.text

    # --------------------------------------------
    # HORÁRIOS
    # --------------------------------------------

    horas = extrair_variavel(texto, "wg_fcst_tab_data_1")

    # --------------------------------------------
    # TENTA GFS
    # --------------------------------------------

    gfs = extrair_variavel(texto, "wg_fcst_tab_data_2")

    # --------------------------------------------
    # TENTA GFS-WAVE
    # --------------------------------------------

    gfs_wave = extrair_variavel(
        texto,
        "wg_fcst_tab_data_3"
    )

    if gfs is None:
        raise Exception("Não encontrei dados GFS")

    if gfs_wave is None:
        gfs_wave = gfs

    return texto, gfs, gfs_wave


def localizar_dados(texto):

    """
    Esta função procura os arrays internos do Windguru.
    """

    nomes = [
        "hours",
        "WINDSPD",
        "GUST",
        "WINDDIR",
        "HTSGW",
        "PERPW",
        "DIRPW",
        "SWELL1",
        "SWPER1",
        "SWDIR1"
    ]

    resultado = {}

    for nome in nomes:

        padroes = [
            rf'"{nome}"\s*:\s*(\[[^\]]*\])',
            rf"'{nome}'\s*:\s*(\[[^\]]*\])",
            rf'{nome}\s*:\s*(\[[^\]]*\])'
        ]

        encontrado = None

        for padrao in padroes:

            m = re.search(
                padrao,
                texto
            )

            if m:

                try:
                    encontrado = json.loads(
                        m.group(1)
                    )
                    break

                except:
                    pass

        resultado[nome] = encontrado

    return resultado


def gerar_previsao():

    texto, gfs, gfs_wave = buscar_windguru()

    dados = localizar_dados(texto)

    horas = dados.get("hours")

    if not horas:
        raise Exception(
            "Não foi possível localizar o array de horários do Windguru"
        )

    # --------------------------------------------
    # arrays
    # --------------------------------------------

    windspd = dados.get("WINDSPD")
    gust = dados.get("GUST")
    winddir = dados.get("WINDDIR")

    htsgw = dados.get("HTSGW")
    perpw = dados.get("PERPW")
    dirpw = dados.get("DIRPW")

    swell1 = dados.get("SWELL1")
    swper1 = dados.get("SWPER1")
    swdir1 = dados.get("SWDIR1")

    # --------------------------------------------
    # resultado
    # --------------------------------------------

    dias = {}

    for i, h in enumerate(horas):

        try:

            # Alguns formatos do Windguru usam timestamp
            if isinstance(h, (int, float)):

                dt = datetime.fromtimestamp(
                    h,
                    ZoneInfo("America/Sao_Paulo")
                )

            else:

                continue

        except:

            continue

        if dt.hour not in [6, 12, 15]:
            continue

        dia = str(dt.day)

        if dia not in dias:
            dias[dia] = {
                "data": dia
            }

        chave = f"{dt.hour:02d}"

        def pega(arr):
            if arr is None:
                return None

            if i >= len(arr):
                return None

            return numero(arr[i])

        vento = pega(windspd)
        rajada = pega(gust)
        onda = pega(htsgw)
        periodo = pega(perpw)

        swell = pega(swell1)
        periodo_swell = pega(swper1)

        wd = pega(winddir)
        wv = pega(dirpw)
        sd = pega(swdir1)

        dias[dia][chave] = {
            "onda": onda,
            "periodo": periodo,
            "direcao": direcao_graus(wv),

            "swell": swell,
            "periodo_swell": periodo_swell,
            "direcao_swell": direcao_graus(sd),

            "vento": kmh(vento),
            "rajada": kmh(rajada),
            "vento_dir": direcao_graus(wd)
        }

    lista = list(dias.values())

    return lista[:4]


@app.get("/")
def inicio():

    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": SPOT
    }


@app.get("/garopaba")
def garopaba():

    try:

        dias = gerar_previsao()

        return {
            "status": "ok",
            "local": "Garopaba",
            "windguru_spot": SPOT,
            "unidade_onda": "metros",
            "unidade_vento": "km/h",
            "horarios": [
                "06",
                "12",
                "15"
            ],
            "dias": dias
        }

    except Exception as e:

        return {
            "status": "erro",
            "mensagem": str(e)
        }
