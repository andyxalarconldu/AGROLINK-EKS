Set-Content -Path "README.md" -Encoding utf8 -Value @'
# AgroLink Andes · Despachos dirigidos por eventos en Kubernetes (AWS)

![Terraform](https://img.shields.io/badge/Terraform-%E2%89%A51.10-7B42BC?logo=terraform&logoColor=white)
![EKS](https://img.shields.io/badge/AWS-EKS%20%7C%20RDS%20%7C%20ECR-FF9900?logo=amazonaws&logoColor=white)
![Kafka](https://img.shields.io/badge/Kafka-3.8%20KRaft-231F20?logo=apachekafka&logoColor=white)
![Python](https://img.shields.io/badge/Python-FastAPI-3776AB?logo=python&logoColor=white)

Examen complexivo · Programación Distribuida · Caso 2
Universidad Central del Ecuador · **Autor:** Andy Alarcon

## Qué hace

Plataforma que procesa las guías de despacho de AgroLink Andes. En cosecha el volumen se multiplica por diez y el sistema anterior perdía registros. Aquí cada guía viaja como un **evento**:

1. El **productor** recibe la guía por HTTP (`POST /despachos`) y la publica en Kafka.
2. El **inventario** la lee, descuenta el stock en una base PostgreSQL privada y publica el resultado.
3. La **notificación** lee el resultado y avisa al transportista.

Cada parte escala por separado, ninguna guía se pierde si cae un pod, y la base de datos no es accesible desde Internet.

## Arquitectura

```mermaid
flowchart LR
    C[Cliente] -->|HTTP| LB[LoadBalancer]
    LB --> P[Productor]
    subgraph EKS[EKS - subredes privadas]
        P -->|clave id_centro_acopio| T1[(despachos<br/>3 particiones)]
        T1 --> I[Inventario<br/>HPA 1 a 3]
        T1 --> T2[(inventario-resultado)]
        T2 --> N[Notificación]
    end
    I --> DB[(RDS privada)]
    N --> DB