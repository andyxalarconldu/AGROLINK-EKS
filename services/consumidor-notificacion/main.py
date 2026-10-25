# CONSUMIDOR DE NOTIFICACIÓN (grupo "notificacion")
# Lee el resultado del inventario y notifica al transportista.
# Escala de forma independiente del inventario.
# ==========================================================
import os, json, time, threading, logging
import psycopg2
from fastapi import FastAPI, HTTPException
from confluent_kafka import Consumer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("notificacion")

# --- Configuración por variables de entorno ---
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC_IN = os.environ.get("TOPIC_IN", "inventario-resultado")   # lee el RESULTADO del inventario
DB = dict(host=os.environ["DB_HOST"], dbname=os.environ.get("DB_NAME", "inventario"),
          user=os.environ.get("DB_USER", "agrolink"), password=os.environ["DB_PASSWORD"],
          connect_timeout=5)

app = FastAPI(title="AgroLink - Consumidor de notificación")
estado = {"consumidor_vivo": False}


def conectar():
    """Conecta a la BD; si no responde, reintenta cada 3 s."""
    while True:
        try:
            return psycopg2.connect(**DB)
        except Exception as e:
            log.warning("BD no disponible: %s", e); time.sleep(3)


def bucle():
    conn = conectar()
    consumer = Consumer({"bootstrap.servers": BOOTSTRAP,
                         "group.id": "notificacion",       # OTRO grupo: escala por separado
                         "enable.auto.commit": False,      # commit manual
                         "auto.offset.reset": "earliest"})
    consumer.subscribe([TOPIC_IN])
    estado["consumidor_vivo"] = True

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            log.error(msg.error()); continue
        try:
            ev = json.loads(msg.value())
            if ev["estado_guia"] == "inventario_descontado":
                # Simulación de la notificación (en producción: correo, SMS, API...)
                log.info("NOTIFICANDO al transportista %s: guía %s, %s kg de %s hacia %s",
                         ev["id_transportista"], ev["id_guia"], ev["cantidad_kg"],
                         ev["producto"], ev["destino"])
                with conn, conn.cursor() as cur:
                    # Idempotente: solo cambia si todavía está en "inventario_descontado"
                    cur.execute("UPDATE guias SET estado_guia='notificada' "
                                "WHERE id_guia=%s AND estado_guia='inventario_descontado'",
                                (ev["id_guia"],))
            else:
                # Las rechazadas no generan despacho
                log.info("Guía %s %s: no se notifica despacho", ev["id_guia"], ev["estado_guia"])
            consumer.commit(msg, asynchronous=False)       # commit después de procesar
        except Exception as e:
            log.exception("Error, se reintentará: %s", e)
            try: conn.rollback()
            except Exception: conn = conectar()
            time.sleep(2)


@app.on_event("startup")
def iniciar():
    threading.Thread(target=bucle, daemon=True).start()   # consumidor en segundo plano


@app.get("/health")      # liveness
def health():
    return {"status": "UP"}


@app.get("/ready")       # readiness
def ready():
    if not estado["consumidor_vivo"]:
        raise HTTPException(503, "Consumidor no suscrito aún")
    return {"status": "READY"}