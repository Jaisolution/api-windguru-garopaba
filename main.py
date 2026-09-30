        "versao": "10.0"
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
# TESTE SOMENTE MARES - 5 DIAS
# =====================================================

@app.get("/mares")
def mares():

    dados = buscar_mares_tabuademares()

    return {
        "status": "ok" if dados else "sem_dados",
        "local": "Garopaba",
        "fonte": "Tabua de Mares",
        "dias": dados
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

        # Tabua de Mares - Garopaba / proximos 5 dias
        dias_mares = buscar_mares_tabuademares()

        dias = adicionar_mares_aos_dias(
            dias,
            dias_mares
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

            "fonte_mare": "Tabua de Mares - Garopaba",

            "dias": dias
        }

    except Exception as erro:

        return {
            "status": "erro",
            "erro": str(erro)
        }
