# PRODUCTOR: recibe guías por HTTP y las publica en Kafka.
# Swagger se genera solo en /docs
# ==========================================================

# --- Importaciones: las "herramientas" que usa el programa ---
import os, json                          # os: leer variables de entorno; json: convertir a texto
from datetime import datetime, timezone  # para poner la fecha/hora de emisión
from uuid import uuid4                   # genera identificadores únicos

from fastapi import FastAPI, HTTPException   # FastAPI crea la API y Swagger
from pydantic import BaseModel, Field        # define y valida los campos
from confluent_kafka import Producer         # cliente para ENVIAR mensajes a Kafka

# --- Configuración: viene de variables de entorno (la inyecta Kubernetes) ---
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "kafka:9092")  # dirección de Kafka
TOPIC = os.environ.get("TOPIC", "despachos")                 # tópico donde publica

# Crea la aplicación. El título aparece en Swagger (/docs)
app = FastAPI(title="AgroLink - Productor de despachos", version="1.0")

# acks=all: Kafka confirma solo cuando guardó el mensaje (no se pierde)
producer = Producer({"bootstrap.servers": BOOTSTRAP, "acks": "all"})


# --- Modelo de datos: campos del diccionario del examen + validación ---
class Despacho(BaseModel):
    id_guia: str = Field(default_factory=lambda: str(uuid4()))  # único por guía (si no lo envías, se genera)
    id_centro_acopio: str                                       # bodega de origen = CLAVE DE PARTICIÓN
    destino: str                                                # mercado o planta de destino
    id_transportista: str                                       # transportista asignado
    producto: str                                               # producto despachado
    cantidad_kg: float = Field(gt=0)                            # debe ser mayor a 0 (si no, error 422)


# --- Endpoint principal: recibir una guía ---
@app.post("/despachos", status_code=202)   # 202 = "aceptado, se procesará después" (asíncrono)
def crear_despacho(d: Despacho):
    evento = d.model_dump()                                           # convierte el modelo a diccionario
    evento["fecha_despacho"] = datetime.now(timezone.utc).isoformat() # fecha de emisión
    evento["estado_guia"] = "emitida"                                 # primer estado del flujo
    try:
        # key = id_centro_acopio -> misma bodega = misma partición = orden preservado (PUNTO 4)
        producer.produce(TOPIC, key=d.id_centro_acopio, value=json.dumps(evento))
        producer.flush(5)   # espera hasta 5 s la confirmación de Kafka
    except Exception as e:
        raise HTTPException(503, f"Kafka no disponible: {e}")
    return {"id_guia": d.id_guia, "estado_guia": "emitida"}


# --- Sonda LIVENESS (punto 5): "¿el proceso está vivo?" Si falla, Kubernetes reinicia el pod ---
@app.get("/health")
def health():
    return {"status": "UP"}


# --- Sonda READINESS (punto 6): "¿puede atender tráfico?" Depende de Kafka ---
# Si Kafka cae, el pod sale del balanceador SIN reiniciarse.
@app.get("/ready")
def ready():
    try:
        producer.list_topics(timeout=3)   # pregunta a Kafka si responde
        return {"status": "READY"}
    except Exception:
        raise HTTPException(503, "Kafka no responde")