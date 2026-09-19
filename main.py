import requests
import re
from html import unescape


URL = "https://old.windguru.cz/zht/index.php?sc=209196"


print("========================================")
print(" TESTE TEMPERATURA DA AGUA - WINDGURU")
print(" GAROPABA - SPOT 209196")
print("========================================")
print()


# ============================================================
# BAIXAR PAGINA
# ============================================================

try:

    resposta = requests.get(
        URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        },
        timeout=30
    )

    resposta.raise_for_status()

    html = resposta.text

    print("Pagina baixada com sucesso!")
    print("Tamanho:", len(html), "caracteres")
    print()

except Exception as erro:

    print("ERRO AO BAIXAR WINDGURU:")
    print(erro)
    exit()


# ============================================================
# CONVERTER HTML PARA TEXTO
# ============================================================

texto = unescape(html)

texto_sem_tags = re.sub(
    r"<[^>]+>",
    " ",
    texto
)

texto_sem_tags = re.sub(
    r"\s+",
    " ",
    texto_sem_tags
)


# ============================================================
# PROCURAR TODAS AS TEMPERATURAS
# ============================================================

print("========================================")
print(" TEMPERATURAS ENCONTRADAS")
print("========================================")
print()


padroes = [

    # Exemplo: 16 °C
    r'(-?\d{1,2}(?:[.,]\d+)?)\s*°\s*C',

    # Exemplo: 16°C
    r'(-?\d{1,2}(?:[.,]\d+)?)\s*&deg;\s*C',

    # Exemplo: 16 C
    r'(-?\d{1,2}(?:[.,]\d+)?)\s+C\b'
]


encontrados = []


for padrao in padroes:

    for resultado in re.finditer(
        padrao,
        texto_sem_tags,
        re.IGNORECASE
    ):

        temperatura = resultado.group(1)

        inicio = max(
            0,
            resultado.start() - 250
        )

        fim = min(
            len(texto_sem_tags),
            resultado.end() + 250
        )

        contexto = texto_sem_tags[
            inicio:fim
        ]

        registro = (
            temperatura,
            contexto
        )

        if registro not in encontrados:

            encontrados.append(
                registro
            )


# ============================================================
# MOSTRAR RESULTADOS
# ============================================================

if not encontrados:

    print("Nenhuma temperatura encontrada.")
    print()

else:

    print(
        "Total encontrado:",
        len(encontrados)
    )

    print()

    for numero, item in enumerate(
        encontrados,
        start=1
    ):

        temperatura = item[0]
        contexto = item[1]

        print("----------------------------------------")
        print("RESULTADO", numero)
        print("----------------------------------------")

        print(
            "Temperatura:",
            temperatura,
            "C"
        )

        print()

        print("CONTEXTO:")

        print(contexto)

        print()


# ============================================================
# PROCURAR PALAVRAS RELACIONADAS A AGUA
# ============================================================

print()
print("========================================")
print(" BUSCA POR PALAVRAS RELACIONADAS A AGUA")
print("========================================")
print()


palavras = [
    "water",
    "water temp",
    "water temperature",
    "sea temp",
    "sea temperature",
    "watertemp",
    "temp water",
    "agua",
    "água",
    "temperatura da agua",
    "temperatura da água"
]


achou_palavra = False


for palavra in palavras:

    for resultado in re.finditer(
        re.escape(palavra),
        texto,
        re.IGNORECASE
    ):

        achou_palavra = True

        inicio = max(
            0,
            resultado.start() - 300
        )

        fim = min(
            len(texto),
            resultado.end() + 500
        )

        contexto = texto[
            inicio:fim
        ]

        contexto = re.sub(
            r"\s+",
            " ",
            contexto
        )

        print("----------------------------------------")

        print(
            "PALAVRA:",
            palavra
        )

        print()

        print(contexto)

        print()


if not achou_palavra:

    print(
        "Nenhuma palavra relacionada a temperatura "
        "da agua foi encontrada."
    )


# ============================================================
# PROCURAR VALORES PERTO DA LATITUDE DE GAROPABA
# ============================================================

print()
print("========================================")
print(" CONTEXTO DA LATITUDE DE GAROPABA")
print("========================================")
print()


for resultado in re.finditer(
    r'Lat[^0-9-]*-28',
    texto_sem_tags,
    re.IGNORECASE
):

    inicio = max(
        0,
        resultado.start() - 200
    )

    fim = min(
        len(texto_sem_tags),
        resultado.end() + 1500
    )

    print(
        texto_sem_tags[inicio:fim]
    )

    print()
    print("----------------------------------------")
    print()


print()
print("========================================")
print(" TESTE FINALIZADO")
print("========================================")
