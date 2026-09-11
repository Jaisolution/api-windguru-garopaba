python
from fastapi import FastAPI

app = FastAPI(
    title="API Windguru Garopaba",
    description="API de previsão para o projeto ESP32",
    version="1.0.0"
)


@app.get("/")
def inicio():
    return {
        "status": "online",
        "api": "Windguru Garopaba",
        "spot": 209196
    }


@app.get("/garopaba")
def garopaba():
    return {
        "local": "Garopaba",
        "windguru_spot": 209196,
        "previsao": [],
        "mensagem": "API funcionando. A extração dos dados será adicionada."
    }
