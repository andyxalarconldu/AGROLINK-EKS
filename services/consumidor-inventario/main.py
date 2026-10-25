# ==========================================================
# CONSUMIDOR DE INVENTARIO (grupo "inventario")
# Lee guías de "despachos", descuenta stock en PostgreSQL y
# publica el resultado en "inventario-resultado".
# Garantía: at-least-once + idempotencia por id_guia.
# ==========================================================
import os, json, time, threading, logging
import psycopg2
from fastapi import FastAPI, HTTPException
from confluent_kafka import Consumer, Producer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("inventario")

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC_IN = os.environ.get("TOPIC_IN", "despachos")
TOPIC_OUT = os.environ.get("TOPIC_OUT", "inventario-resultado")
DB = dict(
    host=os.environ["DB_HOST"],
    dbname=os.environ.get("DB_NAME", "inventario"),
    user=os.environ.get("DB_USER", "agrolink"),
    password=os.environ["DB_PASSWORD"],   # viene de un Secret de Kubernetes
    connect_timeout=5,
)

app = FastAPI(title="AgroLink - Consumidor de inventario")
estado = {"consumidor_vivo": False}

# Tablas y stock inicial (la app se autoconfigura al arrancar)
SCHEMA = """
CREATE TABLE IF NOT EXISTS inventario (
    id_centro_acopio TEXT, producto TEXT, stock_kg NUMERIC NOT NULL,
    PRIMARY KEY (id_centro_acopio, producto));
CREATE TABLE IF NOT EXISTS guias (
    id_guia TEXT PRIMARY KEY,                 -- UNIQUE: base de la idempotencia
    id_centro_acopio TEXT, destino TEXT, id_transportista TEXT,
    producto TEXT, cantidad_kg NUMERIC, fecha_despacho TIMESTAMPTZ,
    estado_guia TEXT, stock_resultante NUMERIC,
    particion_asignada INT, intentos_proceso INT DEFAULT 1);
INSERT INTO inventario VALUES
 ('BOD-01','papa',100000),('BOD-01','maiz',100000),('BOD-01','cebolla',100000),
 ('BOD-02','papa',100000),('BOD-02','maiz',100000),('BOD-02','cebolla',100000),
 ('BOD-03','papa',100000),('BOD-03','maiz',100000),('BOD-03','cebolla',100000)
ON CONFLICT DO NOTHING;
"""


def conectar():
    while True:                                # reintenta hasta que la BD responda
        try:
            c = psycopg2.connect(**DB)
            with c, c.cursor() as cur:
                cur.execute(SCHEMA)            # crea tablas y stock inicial si no existen
            return c
        except Exception as e:
            log.warning("BD no disponible: %s", e)
            time.sleep(3)


def procesar(conn, ev, particion):
    """Una sola transacción: o se hace todo o no se hace nada."""
    with conn, conn.cursor() as cur:
        # Inserta la guía. Si ya existía (reentrega), solo suma 1 al contador.
        cur.execute("""
            INSERT INTO guias (id_guia,id_centro_acopio,destino,id_transportista,
                producto,cantidad_kg,fecha_despacho,estado_guia,particion_asignada)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'emitida',%s)
            ON CONFLICT (id_guia)
            DO UPDATE SET intentos_proceso = guias.intentos_proceso + 1
            RETURNING estado_guia, stock_resultante, intentos_proceso""",
            (ev["id_guia"], ev["id_centro_acopio"], ev["destino"], ev["id_transportista"],
             ev["producto"], ev["cantidad_kg"], ev["fecha_despacho"], particion))
        est, stock, intentos = cur.fetchone()

        if est != "emitida":                   # YA procesada: NO se descuenta dos veces
            log.info("Guía %s reentregada (intento %s), se omite el descuento", ev["id_guia"], intentos)
            return est, stock, intentos

        # Descuento atómico: solo si alcanza el stock.
        cur.execute("""UPDATE inventario SET stock_kg = stock_kg - %s
                       WHERE id_centro_acopio=%s AND producto=%s AND stock_kg >= %s
                       RETURNING stock_kg""",
                    (ev["cantidad_kg"], ev["id_centro_acopio"], ev["producto"], ev["cantidad_kg"]))
        fila = cur.fetchone()
        if fila:
            est, stock = "inventario_descontado", fila[0]
        else:                                  # sin stock suficiente
            cur.execute("SELECT stock_kg FROM inventario WHERE id_centro_acopio=%s AND producto=%s",
                        (ev["id_centro_acopio"], ev["producto"]))
            r = cur.fetchone()
            est, stock = "rechazada", (r[0] if r else 0)

        cur.execute("UPDATE guias SET estado_guia=%s, stock_resultante=%s WHERE id_guia=%s",
                    (est, stock, ev["id_guia"]))
        return est, stock, intentos


def bucle():
    conn = conectar()
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": "inventario",              # GRUPO DE CONSUMIDORES
        "enable.auto.commit": False,           # commit MANUAL, después de procesar
        "auto.offset.reset": "earliest",
    })
    producer = Producer({"bootstrap.servers": BOOTSTRAP, "acks": "all"})
    consumer.subscribe([TOPIC_IN])
    estado["consumidor_vivo"] = True
    log.info("Consumidor 'inventario' suscrito a %s", TOPIC_IN)

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            log.error(msg.error()); continue
        try:
            ev = json.loads(msg.value())
            est, stock, intentos = procesar(conn, ev, msg.partition())
            ev.update(estado_guia=est, stock_resultante=float(stock or 0),
                      particion_asignada=msg.partition(), intentos_proceso=intentos)
            producer.produce(TOPIC_OUT, key=ev["id_centro_acopio"], value=json.dumps(ev, default=str))
            producer.flush(5)
            consumer.commit(msg, asynchronous=False)   # SOLO ahora se marca como leído
            log.info("Guía %s -> %s | stock=%s | partición=%s | intento=%s",
                     ev["id_guia"], est, stock, msg.partition(), intentos)
        except Exception as e:
            # Sin commit: Kafka reentrega el mensaje (no se pierde la guía).
            log.exception("Error procesando, se reintentará: %s", e)
            try: conn.rollback()
            except Exception: conn = conectar()
            time.sleep(2)


@app.on_event("startup")
def iniciar():
    threading.Thread(target=bucle, daemon=True).start()   # consumidor en segundo plano


@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/ready")
def ready():
    if not estado["consumidor_vivo"]:
        raise HTTPException(503, "Consumidor no suscrito aún")
    return {"status": "READY"}


# ---------- ENDPOINTS DE CONSULTA (para la demo en Swagger) ----------
# La BD es privada: no se puede consultar desde mi PC.
# Estos endpoints leen la BD desde dentro del clúster.

@app.get("/guias")
def listar_guias(limite: int = 50):
    """Últimas guías: estado, partición asignada e intentos de proceso."""
    c = psycopg2.connect(**DB)
    try:
        with c.cursor() as cur:
            cur.execute("""SELECT id_guia, id_centro_acopio, producto, cantidad_kg,
                                  estado_guia, stock_resultante, particion_asignada, intentos_proceso
                           FROM guias ORDER BY fecha_despacho DESC LIMIT %s""", (limite,))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, [float(v) if hasattr(v, "as_tuple") else v for v in r]))
                    for r in cur.fetchall()]
    finally:
        c.close()


@app.get("/guias/resumen")
def resumen():
    """Total de guías por estado y total de reintentos."""
    c = psycopg2.connect(**DB)
    try:
        with c.cursor() as cur:
            cur.execute("SELECT estado_guia, COUNT(*) FROM guias GROUP BY estado_guia")
            por_estado = {e: n for e, n in cur.fetchall()}
            cur.execute("SELECT COUNT(*), COALESCE(SUM(intentos_proceso - 1), 0) FROM guias")
            total, reintentos = cur.fetchone()
            return {"total_guias": total, "reintentos": int(reintentos), "por_estado": por_estado}
    finally:
        c.close()


@app.get("/inventario")
def stock():
    """Existencias actuales por bodega y producto."""
    c = psycopg2.connect(**DB)
    try:
        with c.cursor() as cur:
            cur.execute("SELECT id_centro_acopio, producto, stock_kg FROM inventario ORDER BY 1, 2")
            return [{"id_centro_acopio": a, "producto": b, "stock_kg": float(s)} for a, b, s in cur.fetchall()]
    finally:
        c.close()