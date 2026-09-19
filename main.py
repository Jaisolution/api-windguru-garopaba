# ============================================================
# DEBUG CABECALHO WINDGURU
# ============================================================

@app.get("/debug-cabecalho")
def debug_cabecalho():

    try:

        html = baixar_windguru()

        resultados = []

        # Procura trechos que tenham horarios HH:MM
        for encontrado in re.finditer(
            r'\d{1,2}:\d{2}',
            html
        ):

            inicio = max(
                0,
                encontrado.start() - 250
            )

            fim = min(
                len(html),
                encontrado.end() + 250
            )

            trecho = html[inicio:fim]

            resultados.append(
                trecho
            )

            if len(resultados) >= 30:
                break

        # Procura trechos relacionados a temperatura
        temperatura = []

        palavras = [
            "water",
            "Water",
            "WATER",
            "sea",
            "Sea",
            "temp_water",
            "water_temp"
        ]

        for palavra in palavras:

            pos = html.find(palavra)

            if pos >= 0:

                inicio = max(
                    0,
                    pos - 300
                )

                fim = min(
                    len(html),
                    pos + 500
                )

                temperatura.append(
                    html[inicio:fim]
                )

        return {
            "status": "ok",
            "horarios": resultados,
            "temperatura": temperatura
        }

    except Exception as erro:

        return {
            "status": "erro",
            "erro": str(erro)
        }
