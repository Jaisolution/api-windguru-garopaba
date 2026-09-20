from fastapi import FastAPI
import requests
import json
import re

app = FastAPI(
    title="API Windguru Garopaba",
    description="API de previsão para ESP32",
    version="9.1"
)

# =====================================================
# CONFIGURAÇÕES
# =====================================================

WINDGURU_URL = "https://old.windguru.cz/zht/index.php?sc=209196"

SURF_FORECAST_URL = "https://pt.surf-forecast.com/breaks/Praiade-Garopaba/seatemp"

HORARIOS = ["06", "12", "18"]
MAX_DIAS = 4


# =====================================================
# BAIXAR WINDGURU
# =====================================================

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


# =====================================================
# TEMPERATURA DA ÁGUA - SURF FORECAST
# =====================================================

def buscar_temperatura_agua():

    try:

        resposta = requests.get(
            SURF_FORECAST_URL,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                ),
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
            },
            timeout=20
        )

        resposta.raise_for_status()

        html = resposta.text

        # -------------------------------------------------
        # TENTATIVA 1
        # -------------------------------------------------

        padrao1 = (
            r'temperatura da [áa]gua do mar de '
            r'Praia de Garopaba hoje [ée]'
            r'.{0,300}?'
            r'([0-9]{1,2}(?:[.,][0-9])?)'
            r'\s*(?:°|&deg;)?\s*C'
        )

        resultado = re.search(
            padrao1,
            html,
            re.IGNORECASE | re.DOTALL
        )

        if resultado:

            temperatura = resultado.group(1)

            temperatura = temperatura.replace(",", ".")

            return round(float(temperatura), 1)

        # -------------------------------------------------
        # TENTATIVA 2
        # -------------------------------------------------

        padrao2 = (
            r'temperatura do mar hoje em Praia de Garopaba'
            r'.{0,300}?'
            r'([0-9]{1,2}(?:[.,][0-9])?)'
            r'\s*(?:°|&deg;)?\s*C'
        )

        resultado = re.search(
            padrao2,
            html,
            re.IGNORECASE | re.DOTALL
        )

        if resultado:

            temperatura = resultado.group(1)

            temperatura = temperatura.replace(",", ".")

            return round(float(temperatura), 1)

        # -------------------------------------------------
        # TENTATIVA 3
        # -------------------------------------------------

        padrao3 = (
            r'(?:sea temperature|water temperature|'
            r'temperatura da [áa]gua)'
            r'.{0,200}?'
            r'([0-9]{1,2}(?:[.,][0-9])?)'
            r'\s*(?:°|&deg;)?\s*C'
        )

        resultado = re.search(
            padrao3,
            html,
            re.IGNORECASE | re.DOTALL
        )

        if resultado:

            temperatura = resultado.group(1)

            temperatura = temperatura.replace(",", ".")

            return round(float(temperatura), 1)

        print("Temperatura da agua nao encontrada no Surf-Forecast")

        return None

    except Exception as erro:

        print(
            "Erro ao buscar temperatura da agua:",
            erro
        )

        return None


# =====================================================
# EXTRAIR MODELOS DO WINDGURU
# =====================================================

def extrair_modelos(html):

    modelos = {}

    padrao = r'var\s+wg_fcst_tab_data_(\d+)\s*=\s*'

    for encontrado in re.finditer(
        padrao,
        html
    ):

        try:

            inicio = encontrado.end()

            decoder = json.JSONDecoder()

            dados, tamanho = decoder.raw_decode(
                html[inicio:]
            )

            fcst = dados.get(
                "fcst",
                {}
            )

            id_model = str(
                dados.get("id_model")
            )

            if id_model in fcst:

                previsao = fcst[
                    id_model
                ]

            elif fcst:

                primeira_chave = list(
                    fcst.keys()
                )[0]

                previsao = fcst[
                    primeira_chave
                ]

            else:

                continue

            modelos[
                dados.get("model")
            ] = previsao

        except Exception:

            continue

    return modelos


# =====================================================
# PEGAR VALOR DA LISTA
# =====================================================

def valor(lista, indice):

    if not isinstance(
        lista,
        list
    ):
        return None

    if indice >= len(lista):
        return None

    return lista[indice]


# =====================================================
# CONVERTER PARA NÚMERO
# =====================================================

def numero(valor_recebido):

    if valor_recebido is None:
        return None

    try:

        return round(
            float(valor_recebido),
            1
        )

    except Exception:

        return None


# =====================================================
# CONVERTER NÓS PARA KM/H
# =====================================================

def no_para_kmh(valor_recebido):

    if valor_recebido is None:
        return None

    try:

        return round(
            float(valor_recebido) * 1.852,
            1
        )

    except Exception:

        return None


# =====================================================
# DIREÇÃO EM GRAUS PARA BÚSSOLA
# =====================================================

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


# =====================================================
# MONTAR PREVISÃO
# =====================================================

def montar_dias(modelos):

    ondas = modelos.get("gfsw")
    tempo = modelos.get("gfs")

    if not ondas:
        return []

    if not tempo:
        return []

    horas_ondas = ondas.get(
        "hours",
        []
    )

    horas_tempo = tempo.get(
        "hours",
        []
    )

    dias = {}

    # =================================================
    # PERCORRER HORÁRIOS DAS ONDAS
    # =================================================

    for i, hora in enumerate(
        horas_ondas
    ):

        hora_wg = valor(
            ondas.get("hr_h"),
            i
        )

        dia_wg = valor(
            ondas.get("hr_d"),
            i
        )

        if hora_wg is None:
            continue

        if dia_wg is None:
            continue

        hora_formatada = str(
            hora_wg
        ).zfill(2)

        # -------------------------------------------------
        # SOMENTE 06 / 12 / 18
        # -------------------------------------------------

        if hora_formatada not in HORARIOS:
            continue

        # -------------------------------------------------
        # ENCONTRAR MESMO HORÁRIO NO GFS
        # -------------------------------------------------

        indice_tempo = None

        for j, hora_tempo in enumerate(
            horas_tempo
        ):

            if hora_tempo == hora:

                indice_tempo = j

                break

        if indice_tempo is None:
            continue

        chave_dia = str(
            dia_wg
        )

        if chave_dia not in dias:

            dias[chave_dia] = {

                "data": chave_dia,

                "horarios": {}
            }

        # =================================================
        # ONDAS
        # =================================================

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

        # =================================================
        # SWELL
        # =================================================

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

        # =================================================
        # VENTO
        # =================================================

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

        # =================================================
        # TEMPERATURA DO AR
        # =================================================

        temperatura = numero(
            valor(
                tempo.get("TMP"),
                indice_tempo
            )
        )

        # =================================================
        # NUVENS
        # =================================================

        nuvens = numero(
            valor(
                tempo.get("TCDC"),
                indice_tempo
            )
        )

        if nuvens is None:

            nuvens = 0

        # =================================================
        # CHUVA
        # =================================================

        chuva = numero(
            valor(
                tempo.get("APCP"),
                indice_tempo
            )
        )

        if chuva is None:

            chuva = 0

        # =================================================
        # MONTAR DADOS DO HORÁRIO
        # =================================================

        dados_horario = {

            "onda": onda,

            "periodo": periodo,

            "direcao": direcao_compass(
                direcao_onda
            ),

            "swell": swell,

            "periodo_swell":
                periodo_swell,

            "direcao_swell":
                direcao_compass(
                    direcao_swell
                ),

            "vento": vento,

            "rajada": rajada,

            "vento_dir":
                direcao_compass(
                    direcao_vento
                ),

            "temp":
                temperatura,

            "nuvens":
                nuvens,

            "chuva":
                chuva
        }

        # =================================================
        # MANHÃ / TARDE / NOITE
        # =================================================

        if hora_formatada == "06":

            nome = "manha"

        elif hora_formatada == "12":

            nome = "tarde"

        else:

            nome = "noite"

        dias[
            chave_dia
        ][
            "horarios"
        ][
            nome
        ] = dados_horario

    # =====================================================
    # CONVERTER DICIONÁRIO PARA LISTA
    # =====================================================

    resultado = []

    for dia, dados in dias.items():

        item = {

            "data":
                dados["data"]

        }

        horarios = dados[
            "horarios"
        ]

        if "manha" in horarios:

            item[
                "manha"
            ] = horarios[
                "manha"
            ]

        if "tarde" in horarios:

            item[
                "tarde"
            ] = horarios[
                "tarde"
            ]

        if "noite" in horarios:

            item[
                "noite"
            ] = horarios[
                "noite"
            ]

        resultado.append(
            item
        )

    # =====================================================
    # SOMENTE 4 DIAS
    # =====================================================

    return resultado[
        :MAX_DIAS
    ]


# =====================================================
# ROTA INICIAL
# =====================================================

@app.get("/")
def inicio():

    return {

        "status":
            "online",

        "api":
            "Windguru Garopaba",

        "spot":
            209196,

        "versao":
            "9.1",

        "temperatura_agua_fonte":
            "Surf-Forecast"
    }


# =====================================================
# ROTA GAROPABA
# =====================================================

@app.get("/garopaba")
def garopaba():

    try:

        # =================================================
        # BAIXAR WINDGURU
        # =================================================

        html = baixar_windguru()

        # =================================================
        # EXTRAIR MODELOS
        # =================================================

        modelos = extrair_modelos(
            html
        )

        # =================================================
        # MONTAR PREVISÃO
        # =================================================

        dias = montar_dias(
            modelos
        )

        # =================================================
        # TEMPERATURA DA ÁGUA
        # =================================================

        temperatura_agua = (
            buscar_temperatura_agua()
        )

        # =================================================
        # RESPOSTA DA API
        # =================================================

        return {

            "status":
                "ok",

            "local":
                "Garopaba",

            "windguru_spot":
                209196,

            "unidade_onda":
                "metros",

            "unidade_vento":
                "km/h",

            "temperatura_agua":
                temperatura_agua,

            "unidade_temperatura_agua":
                "C",

            "fonte_temperatura_agua":
                "Surf-Forecast",

            "dias":
                dias
        }

    except Exception as erro:

        return {

            "status":
                "erro",

            "erro":
                str(erro)
        }
