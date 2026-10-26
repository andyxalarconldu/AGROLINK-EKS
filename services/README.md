@'
# services/ · Servicios de la plataforma

Tres servicios en Python 3.11 con FastAPI. Cada uno expone Swagger en `/docs`.

services/
├── productor/
├── consumidor-inventario/
└── consumidor-notificacion/


Cada carpeta contiene `main.py`, `requirements.txt` y `Dockerfile`.

## Flujo

POST /despachos → Productor → tópico despachos → Inventario → tópico inventario-resultado → Notificación
(202) (3 particiones) (RDS) (RDS)


## Servicios

### productor

Recibe guías por HTTP y las publica en Kafka sin esperar su procesamiento.

| Endpoint | Función |
|---|---|
| `POST /despachos` | Valida la guía, genera `id_guia` si no viene y publica con clave `id_centro_acopio`. Responde 202 |
| `GET /health` | Liveness |
| `GET /ready` | Readiness: consulta a Kafka |

Cuerpo de ejemplo:
```json
{
  "id_centro_acopio": "BOD-01",
  "destino": "Mercado Mayorista Quito",
  "id_transportista": "TRANS-001",
  "producto": "papa",
  "cantidad_kg": 100
}
```

Variables: `KAFKA_BOOTSTRAP` (por defecto `kafka:9092`) y `TOPIC` (`despachos`). El productor usa `acks=all`.

### consumidor-inventario

Grupo de consumidores `inventario`. Lee `despachos`, descuenta el stock en PostgreSQL y publica el resultado en `inventario-resultado`.

| Endpoint | Función |
|---|---|
| `GET /health`, `GET /ready` | Sondas. Ready cuando ya se suscribió a Kafka |
| `GET /guias` | Estado, partición asignada e intentos de cada guía |
| `GET /guias/resumen` | Total por estado y reintentos |
| `GET /inventario` | Existencias por bodega y producto |

Variables: `KAFKA_BOOTSTRAP`, `TOPIC_IN`, `TOPIC_OUT`, `DB_HOST`, `DB_NAME`, `DB_USER` y `DB_PASSWORD` (desde un Secret).

Al arrancar crea las tablas `inventario` y `guias` y carga un stock inicial de 100000 kg por producto (`papa`, `maiz`, `cebolla`) en `BOD-01`, `BOD-02` y `BOD-03`.

### consumidor-notificacion

Grupo `notificacion`. Lee `inventario-resultado` y notifica al transportista cuando la guía quedó en `inventario_descontado`; entonces la marca `notificada`. Las rechazadas no generan notificación.

## Garantías de entrega

| Garantía | Cómo se logra |
|---|---|
| Ninguna guía se pierde | `enable.auto.commit=False`: el offset se confirma solo después de guardar en la base. Si el pod muere antes, Kafka reentrega el mensaje |
| Nunca se descuenta dos veces | `id_guia` es clave primaria: una reentrega se detecta, suma 1 a `intentos_proceso` y omite el descuento |
| Nunca hay stock negativo | `UPDATE ... WHERE stock_kg >= cantidad`: si no alcanza, la guía queda `rechazada` |
| Orden por bodega | La clave de partición es `id_centro_acopio` |

## Estados de una guía

`emitida` → `inventario_descontado` → `notificada`, o `rechazada` si no hay stock.

## Dockerfile (igual en los tres)

| Característica | Detalle |
|---|---|
| Multietapa | Una etapa instala las dependencias y la final copia solo lo necesario |
| Usuario no root | `USER 10001` |
| Dependencias fijadas | `requirements.txt` con versiones exactas |
| Puerto | 8000 |

## Construir y publicar

El tag es el hash del commit. ECR es inmutable, así que un cambio de código exige un commit nuevo.

$TAG = git rev-parse --short HEAD
$ACC = aws sts get-caller-identity --query Account --output text
$REG = "$ACC.dkr.ecr.us-east-1.amazonaws.com”
$PASS = aws ecr get-login-password --region us-east-1
docker login --username AWS --password $PASS $REG
docker build -t “$REG/agrolink/productor:$TAG” services/productor
docker push “$REG/agrolink/productor:$TAG”


Repetir con `consumidor-inventario` y `consumidor-notificacion`.

## Comprobar que no corre como root

docker build -t productor-prueba services/productor
docker run --rm productor-prueba whoami


Debe responder `appuser`.
'@ | Set-Content -Encoding utf8 services\README.md