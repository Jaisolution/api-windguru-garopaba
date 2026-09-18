from fastapi import FastAPI
import requests
import json
import re

app = FastAPI(
    title="API Windguru Garopaba",
    description="API de previsão para ESP32",
    version="10.0"
)

WINDGURU_URL = "https://old.windguru.cz/zht/index.php?sc=209196"

HORARIOS = ["06", "12", "18"]
MAX_DIAS = 4


# ============================================================
# BAIXAR WINDGURU
# ============================================================

def baixar_windguru():

    resposta = requests.get(
        WINDGURU_URL,
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


# ============================================================
# EXTRAIR MODELOS DO HTML
# ============================================================

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

            id_model = str(
                dados.get("id_model")
            )

            if id_model in fcst:

                previsao = fcst[id_model]

            elif fcst:

                primeira_chave = list(
                    fcst.keys()
                )[0]

                previsao = fcst[
                    primeira_chave
                ]

            else:

                continue

            nome_modelo = dados.get("model")

            modelos[nome_modelo] = previsao

        except Exception as erro:

            print(
                "Erro ao extrair modelo:",
                erro
            )

            continue

    return modelos


# ============================================================
# PEGAR VALOR DA LISTA
# ============================================================

def valor(lista, indice):

    if not isinstance(lista, list):
        return None

    if indice < 0:
        return None

    if indice >= len(lista):
        return None

    return lista[indice]


# ============================================================
# CONVERTER PARA NUMERO
# ============================================================

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


# ============================================================
# NOS PARA KM/H
# ============================================================

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


# ============================================================
# DIRECAO EM GRAUS PARA PONTOS CARDEAIS
# ============================================================

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

    try:

        indice = int(
            (float(graus) + 11.25) / 22.5
        ) % 16

        return direcoes[indice]

    except Exception:

        return None


# ============================================================
# ENCONTRAR PRECIPITACAO
# ============================================================

def obter_chuva(tempo, indice_tempo):

    # --------------------------------------------------------
    # PRIMEIRO TENTA APCP1
    # Precipitacao acumulada em 1 hora
    # --------------------------------------------------------

    chuva_apcp1 = numero(
        valor(
            tempo.get("APCP1"),
            indice_tempo
        )
    )

    if chuva_apcp1 is not None:

        return {
            "valor": chuva_apcp1,
            "fonte": "APCP1",
            "intervalo": "1h"
        }

    # --------------------------------------------------------
    # SE NAO EXISTIR APCP1, USA APCP
    # Precipitacao acumulada do periodo do modelo
    # --------------------------------------------------------

    chuva_apcp = numero(
        valor(
            tempo.get("APCP"),
            indice_tempo
        )
    )

    if chuva_apcp is not None:

        return {
            "valor": chuva_apcp,
            "fonte": "APCP",
            "intervalo": "3h"
        }

    # --------------------------------------------------------
    # NAO ENCONTROU PRECIPITACAO
    # --------------------------------------------------------

    return {
        "valor": 0.0,
        "fonte": "nenhum",
        "intervalo": "-"
    }


# ============================================================
# MONTAR PREVISAO
# ============================================================

def montar_dias(modelos):

    ondas = modelos.get("gfsw")
    tempo = modelos.get("gfs")

    if not ondas:

        print("Modelo GFSW nao encontrado")

        return []

    if not tempo:

        print("Modelo GFS nao encontrado")

        return []

    # ========================================================
    # MOSTRAR CAMPOS DO GFS NO LOG
    # Isso vai ajudar a verificar APCP / APCP1
    # ========================================================

    print("")
    print("==========================================")
    print("CAMPOS ENCONTRADOS NO GFS")
    print("==========================================")

    for chave in tempo.keys():

        print(chave)

    print("==========================================")
    print("")

    # ========================================================
    # MOSTRAR CAMPOS DE CHUVA
    # ========================================================

    print("PRECIPITACAO DISPONIVEL:")

    if "APCP1" in tempo:

        print(
            "APCP1 encontrado:",
            tempo.get("APCP1")[:10]
            if isinstance(
                tempo.get("APCP1"),
                list
            )
            else tempo.get("APCP1")
        )

    else:

        print("APCP1 NAO encontrado")

    if "APCP" in tempo:

        print(
            "APCP encontrado:",
            tempo.get("APCP")[:10]
            if isinstance(
                tempo.get("APCP"),
                list
            )
            else tempo.get("APCP")
        )

    else:

        print("APCP NAO encontrado")

    print("==========================================")
    print("")

    # ========================================================
    # HORARIOS
    # ========================================================

    horas_ondas = ondas.get(
        "hours",
        []
    )

    horas_tempo = tempo.get(
        "hours",
        []
    )

    dias = {}

    # ========================================================
    # PERCORRER HORARIOS DO MODELO DE ONDAS
    # ========================================================

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

        if (
            hora_wg is None
            or
            dia_wg is None
        ):

            continue

        hora_formatada = str(
            hora_wg
        ).zfill(2)

        # ====================================================
        # SOMENTE:
        # 06 = MANHA
        # 12 = TARDE
        # 18 = NOITE
        # ====================================================

        if hora_formatada not in HORARIOS:

            continue

        # ====================================================
        # ENCONTRAR MESMO HORARIO NO MODELO GFS
        # ====================================================

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

        # ====================================================
        # ONDA
        # ====================================================

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

        # ====================================================
        # SWELL
        # ====================================================

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

        # ====================================================
        # VENTO
        # ====================================================

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

        # ====================================================
        # TEMPERATURA
        # ====================================================

        temperatura = numero(
            valor(
                tempo.get("TMP"),
                indice_tempo
            )
        )

        # ====================================================
        # NUVENS
        # ====================================================

        nuvens = numero(
            valor(
                tempo.get("TCDC"),
                indice_tempo
            )
        )

        if nuvens is None:

            nuvens = 0.0

        # Garante 0 a 100
        if nuvens < 0:

            nuvens = 0.0

        if nuvens > 100:

            nuvens = 100.0

        # ====================================================
        # CHUVA / PRECIPITACAO
        # ====================================================

        dados_chuva = obter_chuva(
            tempo,
            indice_tempo
        )

        chuva = dados_chuva[
            "valor"
        ]

        chuva_fonte = dados_chuva[
            "fonte"
        ]

        chuva_intervalo = dados_chuva[
            "intervalo"
        ]

        # ====================================================
        # LOG PARA TESTAR CHUVA
        # ====================================================

        print(
            "Dia:",
            chave_dia,
            "Hora:",
            hora_formatada,
            "Chuva:",
            chuva,
            "mm",
            "Fonte:",
            chuva_fonte,
            "Intervalo:",
            chuva_intervalo
        )

        # ====================================================
        # DADOS DO HORARIO
        # ====================================================

        dados_horario = {

            # ONDA
            "onda": onda,

            "periodo": periodo,

            "direcao": direcao_compass(
                direcao_onda
            ),

            # SWELL
            "swell": swell,

            "periodo_swell": periodo_swell,

            "direcao_swell": direcao_compass(
                direcao_swell
            ),

            # VENTO
            "vento": vento,

            "rajada": rajada,

            "vento_dir": direcao_compass(
                direcao_vento
            ),

            # TEMPERATURA
            "temp": temperatura,

            # NUVENS
            "nuvens": nuvens,

            # PRECIPITACAO
            "chuva": chuva,

            "chuva_unidade": "mm",

            "chuva_intervalo":
                chuva_intervalo,

            "chuva_fonte":
                chuva_fonte
        }

        # ====================================================
        # NOME DO PERIODO
        # ====================================================

        if hora_formatada == "06":

            nome = "manha"

        elif hora_formatada == "12":

            nome = "tarde"

        else:

            nome = "noite"

        dias[chave_dia][
            "horarios"
        ][nome] = dados_horario

    # ========================================================
    # CONVERTER DICIONARIO PARA LISTA
    # ========================================================

    resultado = []

    for dia, dados in dias.items():

        item = {
            "data": dados["data"]
        }

        horarios = dados[
            "horarios"
        ]

        if "manha" in horarios:

            item["manha"] = horarios[
                "manha"
            ]

        if "tarde" in horarios:

            item["tarde"] = horarios[
                "tarde"
            ]

        if "noite" in horarios:

            item["noite"] = horarios[
                "noite"
            ]

        resultado.append(
            item
        )

    # ========================================================
    # SOMENTE 4 DIAS
    # ========================================================

    return resultado[
        :MAX_DIAS
    ]


# ============================================================
# PAGINA INICIAL
# ============================================================

@app.get("/")
def inicio():

    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": 209196,
        "versao": "10.0"
    }


# ============================================================
# API GAROPABA
# ============================================================

@app.get("/garopaba")
def garopaba():

    try:

        # ====================================================
        # BAIXAR WINDGURU
        # ====================================================

        html = baixar_windguru()

        # ====================================================
        # EXTRAIR MODELOS
        # ====================================================

        modelos = extrair_modelos(
            html
        )

        print("")
        print("==========================================")
        print("MODELOS ENCONTRADOS")
        print("==========================================")

        for modelo in modelos.keys():

            print(modelo)

        print("==========================================")
        print("")

        # ====================================================
        # MONTAR DIAS
        # ====================================================

        dias = montar_dias(
            modelos
        )

        # ====================================================
        # RESPOSTA
        # ====================================================

        return {

            "status": "ok",

            "local": "Garopaba",

            "windguru_spot": 209196,

            "unidade_onda": "metros",

            "unidade_vento": "km/h",

            "unidade_chuva": "mm",

            "dias": dias
        }

    except Exception as erro:

        print(
            "ERRO:",
            str(erro)
        )

        return {
            "status": "erro",
            "erro": str(erro)
        }
