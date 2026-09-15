from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import re

app = FastAPI()

SPOT = 209196

URL = f"https://www.windguru.cz/209196"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
}


# =========================================================
# DIREÇÃO
# =========================================================

def direcao(graus):

    try:
        g = float(graus) % 360
    except:
        return ""

    nomes = [
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

    return nomes[int((g + 11.25) / 22.5) % 16]


# =========================================================
# CONVERSÃO
# =========================================================

def knots_para_kmh(valor):

    try:
        return round(float(valor) * 1.852, 1)
    except:
        return 0


def numero(valor):

    if valor is None:
        return 0

    valor = str(valor).strip()

    if valor in ["", "-", "—", "–"]:
        return 0

    try:
        return float(
            valor.replace(",", ".")
        )
    except:
        return 0


# =========================================================
# LIMPA TEXTO
# =========================================================

def limpar(texto):

    texto = str(texto)

    texto = (
        texto
        .replace("\xa0", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )

    return re.sub(
        r"\s+",
        " ",
        texto
    ).strip()


# =========================================================
# BUSCA WINDGURU
# =========================================================

def baixar_windguru():

    resposta = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    resposta.raise_for_status()

    return resposta.text


# =========================================================
# LOCALIZA LINHA
# =========================================================

def encontrar_linha(tabela, palavras):

    for tr in tabela.find_all("tr"):

        texto = limpar(
            tr.get_text(" ", strip=True)
        ).lower()

        for palavra in palavras:

            if palavra.lower() in texto:

                return tr

    return None


# =========================================================
# EXTRAI CÉLULAS
# =========================================================

def valores_linha(tr):

    if tr is None:
        return []

    valores = []

    for td in tr.find_all(
        ["td", "th"]
    ):

        texto = limpar(
            td.get_text(" ", strip=True)
        )

        valores.append(texto)

    return valores


# =========================================================
# EXTRAI HORÁRIOS
# =========================================================

def extrair_horarios(tabela):

    tr = encontrar_linha(
        tabela,
        [
            "21h",
            "03h",
            "06h",
            "09h",
            "12h",
            "15h"
        ]
    )

    if tr is None:
        return []

    valores = valores_linha(tr)

    resultado = []

    for valor in valores:

        encontrados = re.findall(
            r"\b(\d{1,2})h\b",
            valor
        )

        resultado.extend(
            encontrados
        )

    return resultado


# =========================================================
# EXTRAI NÚMEROS
# =========================================================

def somente_numeros(tr):

    if tr is None:
        return []

    valores = []

    for td in tr.find_all("td"):

        texto = limpar(
            td.get_text(
                " ",
                strip=True
            )
        )

        if texto in [
            "",
            "-",
            "—",
            "–"
        ]:
            valores.append(None)
            continue

        # pega primeiro número
        m = re.search(
            r"-?\d+(?:[.,]\d+)?",
            texto
        )

        if m:

            try:
                valores.append(
                    float(
                        m.group(
                            0
                        ).replace(
                            ",",
                            "."
                        )
                    )
                )

            except:
                valores.append(None)

        else:

            valores.append(None)

    return valores


# =========================================================
# PREVISÃO
# =========================================================

def gerar_previsao():

    html = baixar_windguru()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    tabelas = soup.find_all(
        "table"
    )

    if not tabelas:

        raise Exception(
            "Nenhuma tabela encontrada no Windguru"
        )

    # -----------------------------------------------------
    # Procuramos a tabela que tenha os horários
    # -----------------------------------------------------

    tabela = None

    for t in tabelas:

        texto = limpar(
            t.get_text(
                " ",
                strip=True
            )
        )

        if (
            "06h" in texto
            and "12h" in texto
            and "15h" in texto
            and (
                "Lainetus" in texto
                or "Lainetus (m)" in texto
                or "Tuule kiirus" in texto
            )
        ):

            tabela = t

            break

    if tabela is None:

        # segunda tentativa
        for t in tabelas:

            texto = limpar(
                t.get_text(
                    " ",
                    strip=True
                )
            )

            if (
                "06h" in texto
                and "12h" in texto
                and "15h" in texto
            ):

                tabela = t

                break

    if tabela is None:

        raise Exception(
            "Tabela de previsão do Windguru não encontrada"
        )

    # -----------------------------------------------------
    # HORÁRIOS
    # -----------------------------------------------------

    texto_tabela = limpar(
        tabela.get_text(
            " ",
            strip=True
        )
    )

    # -----------------------------------------------------
    # ENCONTRA AS LINHAS
    # -----------------------------------------------------

    linha_vento = encontrar_linha(
        tabela,
        [
            "Tuule kiirus",
            "Wind speed"
        ]
    )

    linha_rajada = encontrar_linha(
        tabela,
        [
            "Tuule puhangud",
            "Wind gusts"
        ]
    )

    linha_onda = encontrar_linha(
        tabela,
        [
            "Lainetus (m)",
            "Wave height"
        ]
    )

    linha_periodo = encontrar_linha(
        tabela,
        [
            "Laine periood",
            "Wave period"
        ]
    )

    linha_swell = encontrar_linha(
        tabela,
        [
            "Swell (m)"
        ]
    )

    linha_swell_periodo = encontrar_linha(
        tabela,
        [
            "Swell period"
        ]
    )

    # -----------------------------------------------------
    # HORÁRIOS ENCONTRADOS
    # -----------------------------------------------------

    padrao_horas = re.findall(
        r"\b(21h|03h|06h|09h|12h|15h|18h)\b",
        texto_tabela
    )

    if not padrao_horas:

        raise Exception(
            "Horários não encontrados"
        )

    # -----------------------------------------------------
    # ARRAYS
    # -----------------------------------------------------

    vento = somente_numeros(
        linha_vento
    )

    rajada = somente_numeros(
        linha_rajada
    )

    onda = somente_numeros(
        linha_onda
    )

    periodo = somente_numeros(
        linha_periodo
    )

    swell = somente_numeros(
        linha_swell
    )

    swell_periodo = somente_numeros(
        linha_swell_periodo
    )

    # -----------------------------------------------------
    # CONSTRÓI RESULTADO
    # -----------------------------------------------------

    dias = {}

    # Como a tabela pode repetir horários,
    # usamos a sequência encontrada.
    #
    # Cada horário recebe o índice correspondente
    # aos arrays.

    for i, hora_texto in enumerate(
        padrao_horas
    ):

        hora = int(
            hora_texto.replace(
                "h",
                ""
            )
        )

        if hora not in [
            6,
            12,
            15
        ]:
            continue

        # -----------------------------------------------
        # DATA
        # -----------------------------------------------

        # A página mostra os dias antes das horas.
        # Tentamos localizar a data correspondente
        # através do cabeçalho.

        # fallback: usa data atual + posição
        agora = datetime.now(
            ZoneInfo(
                "America/Sao_Paulo"
            )
        )

        dia_numero = agora.day

        # -----------------------------------------------
        # procura dia já existente
        # -----------------------------------------------

        chave = str(
            dia_numero
        )

        if chave not in dias:

            dias[chave] = {
                "data": chave
            }

        pos = i

        # -----------------------------------------------
        # valores
        # -----------------------------------------------

        onda_valor = (
            onda[pos]
            if pos < len(onda)
            else 0
        )

        periodo_valor = (
            periodo[pos]
            if pos < len(periodo)
            else 0
        )

        swell_valor = (
            swell[pos]
            if pos < len(swell)
            else 0
        )

        swell_periodo_valor = (
            swell_periodo[pos]
            if pos < len(swell_periodo)
            else 0
        )

        vento_valor = (
            vento[pos]
            if pos < len(vento)
            else 0
        )

        rajada_valor = (
            rajada[pos]
            if pos < len(rajada)
            else 0
        )

        dias[chave][
            f"{hora:02d}"
        ] = {

            "onda":
                onda_valor,

            "periodo":
                periodo_valor,

            "direcao":
                "",

            "swell":
                swell_valor,

            "periodo_swell":
                swell_periodo_valor,

            "direcao_swell":
                "",

            "vento":
                knots_para_kmh(
                    vento_valor
                ),

            "rajada":
                knots_para_kmh(
                    rajada_valor
                ),

            "vento_dir":
                ""
        }

    resultado = list(
        dias.values()
    )

    return resultado[:4]


# =========================================================
# ROTAS
# =========================================================

@app.get("/")
def inicio():

    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": SPOT,
        "versao": "3.0"
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

    except Exception as erro:

        return {
            "status": "erro",
            "mensagem": str(erro)
        }
