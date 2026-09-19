# ============================================================
# EXTRAIR TEMPERATURA DA AGUA DO WINDGURU
# ============================================================

def extrair_temperatura_agua(html):

    try:

        # Remove as tags HTML
        texto = re.sub(r"<[^>]+>", " ", html)

        # Converte entidades HTML
        texto = unescape(texto)

        # Remove espaços repetidos
        texto = re.sub(r"\s+", " ", texto)

        # Procura o bloco do spot de Garopaba.
        # A temperatura da água aparece depois das
        # informações de latitude/longitude e horários.

        padrao = re.compile(
            r'Lat:\s*-28(?:[.,]\d+)?'
            r'.{0,800}?'
            r'\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}'
            r'.{0,200}?'
            r'(\d{1,2}(?:[.,]\d+)?)\s*°\s*C',
            re.IGNORECASE | re.DOTALL
        )

        resultado = padrao.search(texto)

        if resultado:

            temperatura = float(
                resultado.group(1).replace(",", ".")
            )

            print(
                "Temperatura da agua:",
                temperatura,
                "C"
            )

            return temperatura

        print("Temperatura da agua nao encontrada")

        return None

    except Exception as erro:

        print(
            "Erro temperatura da agua:",
            erro
        )

        return None
