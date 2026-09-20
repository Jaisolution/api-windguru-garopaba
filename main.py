from fastapi import FastAPI
import requests
import json
import re

# =====================================================
# FASTAPI
# =====================================================

app = FastAPI(
    title="API Windguru Garopaba",
    description="API de previsão para ESP32",
    version="9.3"
)

# =====================================================
# CONFIGURACAO
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
# BUSCAR TEMPERATURA DA AGUA
# SURF-FORECAST
# =====================================================

def buscar_temperatura_agua():

    try:

        resposta = requests.get(
            SURF_FORECAST_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
            },
            timeout=20
        )

        resposta.raise_for_status()

        html = resposta.text

        # Remove tags HTML para facilitar a busca
        texto = re.sub(r"<[^>]+>", " ", html)

        texto = (
            texto
            .replace("&nbsp;", " ")
            .replace("&deg;", "°")
            .replace("&#176;", "°")
        )

        texto = re.sub(
            r"\s+",
            " ",
            texto
        )

        # =============================================
        # TENTATIVA 1
        # =============================================

        padrao1 = (
            r"temperatura da [áa]gua do mar de "
            r"Praia de Garopaba hoje [ée]"
            r".{0,150}?"
            r"([0-9]{1,2}(?:[.,][0-9])?)"
            r"\s*°?\s*C"
        )

        resultado = re.search(
            padrao1,
            texto,
            re.IGNORECASE
        )

        if resultado:

            temperatura = (
                resultado
                .group(1)
                .replace(",", ".")
            )

            return round(
                float(temperatura),
                1
            )

        # =============================================
        # TENTATIVA 2
        # =============================================

        padrao2 = (
            r"Praia de Garopaba"
            r".{0,300}?"
            r"([0-9]{1,2}(?:[.,][0-9])?)"
            r"\s*°\s*C"
        )

        resultado = re.search(
            padrao2,
            texto,
            re.IGNORECASE
        )

        if resultado:

            temperatura = (
                resultado
                .group(1)
                .replace(",", ".")
            )

            temperatura = float(
                temperatura
            )

            # Protecao contra capturar numero absurdo
            if 5 <= temperatura <= 35:

                return round(
                    temperatura,
                    1
                )

        # =============================================
        # TENTATIVA 3
        # =============================================

        temperaturas = re.findall(
            r"([0-9]{1,2}(?:[.,][0-9])?)\s*°\s*C",
            texto,
            re.IGNORECASE
        )

        for temp in temperaturas:

            try:

                temp_num = float(
                    temp.replace(",", ".")
                )

                # Faixa plausivel para agua do mar
                if 10 <= temp_num <= 30:

                    return round(
                        temp_num,
                        1
                    )

            except Exception:
                pass

        return None

    except Exception as erro:

        print(
            "Erro temperatura agua:",
            erro
        )

        return None


# =====================================================
# EXTRAIR MODELOS WINDGURU
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
# VALOR DE LISTA
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
# CONVERTER NUMERO
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
# NOS PARA KM/H
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
# DIRECAO
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
# MONTAR DIAS
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

        if hora_wg is None or dia_wg is None:
            continue

        hora_formatada = str(
            hora_wg
        ).zfill(2)

        # Somente 06, 12 e 18
        if hora_formatada not in HORARIOS:
            continue

        # =============================================
        # LOCALIZAR MESMO HORARIO NO GFS
        # =============================================

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

        # =============================================
        # ONDAS
        # =============================================

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

        # =============================================
        # SWELL
        # =============================================

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

        # =============================================
        # VENTO
        # =============================================

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

        # =============================================
        # TEMPERATURA DO AR
        # =============================================

        temperatura = numero(
            valor(
                tempo.get("TMP"),
                indice_tempo
            )
        )

        # =============================================
        # NUVENS - WINDGURU (ALTA / MEDIA / BAIXA)
        # =============================================
        # Na estrutura usada pela tabela do Windguru,
        # "CDC" representa nebulosidade alta/media/baixa.
        # Dependendo da versao do retorno, CDC pode vir:
        # 1) como lista de trios por horario;
        # 2) como lista achatada com 3 valores por horario.
        #
        # Para o display usamos a MEDIA das camadas validas.
        # Isso evita o problema do TCDC marcar 100% apenas
        # porque existe cobertura em algum nivel da atmosfera.

        def limitar_percentual(v):
            v = numero(v)
            if v is None:
                return None
            if v < 0:
                return 0.0
            if v > 100:
                return 100.0
            return v

        def nuvens_cdc(indice):
            cdc = tempo.get("CDC")

            if not isinstance(cdc, list) or len(cdc) == 0:
                return None

            # Formato A: [[alta, media, baixa], ...]
            if indice < len(cdc):
                item = cdc[indice]

                if isinstance(item, (list, tuple)):
                    vals = [
                        limitar_percentual(x)
                        for x in item[:3]
                    ]
                    vals = [x for x in vals if x is not None]

                    if vals:
                        return round(sum(vals) / len(vals), 1)

                # Alguns retornos podem trazer dicionario.
                if isinstance(item, dict):
                    candidatos = []
                    for chave in (
                        "high", "mid", "middle", "low",
                        "alta", "media", "baixa",
                        "HCDC", "MCDC", "LCDC"
                    ):
                        if chave in item:
                            v = limitar_percentual(item.get(chave))
                            if v is not None:
                                candidatos.append(v)

                    if candidatos:
                        return round(
                            sum(candidatos) / len(candidatos),
                            1
                        )

            # Formato B: [alta, media, baixa, alta, media, baixa...]
            base = indice * 3

            if base + 2 < len(cdc):
                vals = [
                    limitar_percentual(cdc[base]),
                    limitar_percentual(cdc[base + 1]),
                    limitar_percentual(cdc[base + 2])
                ]
                vals = [x for x in vals if x is not None]

                if vals:
                    return round(sum(vals) / len(vals), 1)

            return None

        def nuvens_camadas_separadas(indice):
            grupos = (
                ("HCDC", "HCLD"),
                ("MCDC", "MCLD"),
                ("LCDC", "LCLD")
            )

            vals = []

            for grupo in grupos:
                achou = None

                for chave in grupo:
                    lista = tempo.get(chave)

                    if isinstance(lista, list):
                        achou = limitar_percentual(
                            valor(lista, indice)
                        )

                        if achou is not None:
                            break

                if achou is not None:
                    vals.append(achou)

            if vals:
                return round(sum(vals) / len(vals), 1)

            return None

        # Primeiro: o campo CDC da propria tabela Windguru.
        nuvens = nuvens_cdc(indice_tempo)

        # Segundo: campos separados do GFS, se existirem.
        if nuvens is None:
            nuvens = nuvens_camadas_separadas(indice_tempo)

        # Ultimo recurso: TCDC.
        if nuvens is None:
            nuvens = limitar_percentual(
                valor(
                    tempo.get("TCDC"),
                    indice_tempo
                )
            )

        if nuvens is None:
            nuvens = 0

        # =============================================
        # CHUVA
        # =============================================

        chuva = numero(
            valor(
                tempo.get("APCP"),
                indice_tempo
            )
        )

        if chuva is None:
            chuva = 0

        # =============================================
        # DADOS DO HORARIO
        # =============================================

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

        # =============================================
        # MANHA / TARDE / NOITE
        # =============================================

        if hora_formatada == "06":

            nome = "manha"

        elif hora_formatada == "12":

            nome = "tarde"

        else:

            nome = "noite"

        dias[
            chave_dia
        ]["horarios"][
            nome
        ] = dados_horario

    # =================================================
    # TRANSFORMAR EM LISTA
    # =================================================

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

    return resultado[:MAX_DIAS]


# =====================================================
# PAGINA INICIAL
# =====================================================

@app.get("/")
def inicio():

    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": 209196,
        "versao": "9.3"
    }


# =====================================================
# TESTE SOMENTE TEMPERATURA DA AGUA
# =====================================================

@app.get("/agua")
def agua():

    temperatura = buscar_temperatura_agua()

    return {
        "local": "Praia de Garopaba",
        "temperatura_agua": temperatura,
        "unidade": "C",
        "fonte": "Surf-Forecast"
    }


# =====================================================
# API GAROPABA
# =====================================================

@app.get("/garopaba")
def garopaba():

    try:

        # Windguru
        html = baixar_windguru()

        modelos = extrair_modelos(
            html
        )

        dias = montar_dias(
            modelos
        )

        # Surf-Forecast
        temperatura_agua = (
            buscar_temperatura_agua()
        )

        return {

            "status": "ok",

            "local": "Garopaba",

            "windguru_spot": 209196,

            "unidade_onda": "metros",

            "unidade_vento": "km/h",

            "temperatura_agua": temperatura_agua,

            "unidade_temperatura_agua": "C",

            "fonte_temperatura_agua": "Surf-Forecast",

            "dias": dias
        }

    except Exception as erro:

        return {
            "status": "erro",
            "erro": str(erro)
        }
