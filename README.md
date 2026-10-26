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
Qué se destacaRequisitoCómo se cumpleOrden por bodegaLa clave de partición es id_centro_acopioEscalado independienteDos grupos de consumidores; el inventario usa HPA de 1 a 3 podsNinguna guía se pierdeEl offset se confirma solo después de guardar en la baseNunca se descuenta dos vecesid_guia es clave primaria (idempotencia)Base de datos aisladaSubred privada, sin IP pública, 5432 solo desde el SG del clústerDespliegue sin cortesRollingUpdate con maxUnavailable: 0 y sonda readinessInfraestructura reproducibleTerraform con estado remoto en S3 y proveedores fijadosImágenes segurasDockerfile multietapa, usuario no root, tag por hash, ECR inmutableEstructuraCarpetaContenidoDocumentaciónterraform/VPC, EKS, RDS y ECR (28 recursos)terraform/README.mdk8s/Kafka, ConfigMap, productor, inventario con HPA y notificaciónk8s/README.mdservices/Los 3 servicios en Python con su Dockerfileservices/README.mdscripts/Envío de guías y monitor de disponibilidadscripts/README.mddocs/Diagramas e imágenesRequisitosTerraform 1.10+, AWS CLI 2, kubectl, Docker y Python 3.11. Entorno: AWS Academy Learner Lab (us-east-1, rol LabRole).Despliegue resumidoBashcd terraform
terraform init
terraform apply
cd ..
aws eks update-kubeconfig --name agrolink-eks --region us-east-1
Luego se suben las imágenes a ECR, se instala metrics-server, se aplican los manifiestos y se crean los tópicos. El procedimiento completo está en k8s/README.md y services/README.md.Valores que cambian en cada creación: DB_HOST en k8s/01-config.yaml, el ID de cuenta y el tag en las imágenes, y la dirección del LoadBalancer en scripts/.ProbarloAbrir http://DIRECCION-DEL-LB/docs y ejecutar POST /despachos. Debe responder 202.Consultar el inventario (no es público) con un túnel:Bashkubectl port-forward svc/consumidor-inventario 8081:80
En http://localhost:8081/docs: GET /guias, GET /guias/resumen y GET /inventario.Pruebas realizadasIDPruebaResultadoP1Tópico con 3 particionesOKP2Misma clave, misma particiónOKP3Grupos sin retraso (LAG 0)OKP4Escalado de 1 a 3 réplicas con rebalanceoOKP5Borrar un pod durante el envío: 0 guías perdidasOKP6Rolling update del productor: 0 erroresOKP7BD inaccesible desde InternetOKP8HPA bajo cargaOKCosto y limitacionesCosto estimado ~0,27 USD por hora (dos nodos t3.medium, EKS, NAT, RDS y balanceador). Consumo real en el laboratorio: USD 22,1 de 50.Limitaciones del prototipo: un solo broker de Kafka con disco efímero, un NAT, RDS en una zona y rol LabRole. En producción: 3 brokers o MSK, Multi-AZ, un NAT por zona y roles con mínimo privilegio.DestruirBashkubectl delete -f k8s/02-productor.yaml
cd terraform
terraform destroy