@'
# k8s/ · Manifiestos de Kubernetes

Definen cómo se ejecutan Kafka y los tres servicios dentro del clúster EKS. Ningún archivo contiene secretos: la contraseña de la base se crea por comando.

## Archivos y orden de aplicación

| Archivo | Objetos | Qué hace |
|---|---|---|
| `00-kafka.yaml` | Service `kafka`, StatefulSet `kafka` | Broker único Kafka 3.8 en modo KRaft, almacenamiento efímero (`emptyDir`) |
| `01-config.yaml` | ConfigMap `agrolink-config` | `KAFKA_BOOTSTRAP`, `DB_HOST`, `DB_NAME`, `DB_USER` |
| `02-productor.yaml` | Deployment y Service `productor` | 2 réplicas, `RollingUpdate`, Service tipo `LoadBalancer` |
| `03-inventario.yaml` | Deployment, Service y HPA `consumidor-inventario` | Grupo `inventario`, HPA de 1 a 3 réplicas |
| `04-notificacion.yaml` | Deployment y Service `consumidor-notificacion` | Grupo `notificacion`, 1 réplica |

## Antes de aplicar

1. Metrics-server (lo necesita el HPA):
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

2. Secret con la contraseña de la base (no existe como archivo):

cd ../terraform
$DBPASS = terraform output -raw db_password
cd ../k8s
kubectl create secret generic db-secret --from-literal=DB_PASSWORD=$DBPASS

3. Reemplazar los valores del entorno:

| Archivo | Valor | Cómo obtenerlo |
|---|---|---|
| `01-config.yaml` | `DB_HOST` | `terraform output -raw db_endpoint` |
| `02`, `03` y `04` | ID de cuenta y tag en `image` | `aws sts get-caller-identity` y `git rev-parse --short HEAD` |

## Aplicar

kubectl apply -f 00-kafka.yaml
kubectl exec kafka-0 -- /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic despachos --partitions 3 --replication-factor 1
kubectl exec kafka-0 -- /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic inventario-resultado --partitions 3 --replication-factor 1
kubectl apply -f 01-config.yaml
kubectl apply -f 02-productor.yaml
kubectl apply -f 03-inventario.yaml
kubectl apply -f 04-notificacion.yaml


Kafka tiene `AUTO_CREATE_TOPICS=false`, por eso los tópicos se crean a mano con 3 particiones.

## Qué hay configurado en cada Deployment

| Aspecto | Configuración |
|---|---|
| Imagen | ECR con tag igual al hash del commit, sin `latest` |
| Usuario | `runAsNonRoot: true`, `runAsUser: 10001` |
| Recursos | `requests` 100m CPU y 128 Mi; `limits` 500m y 256 Mi |
| Liveness | `GET /health`: reinicia un pod colgado |
| Readiness | `GET /ready`: en el productor depende de Kafka; en los consumidores, de que ya estén suscritos |
| Configuración | `envFrom` del ConfigMap; `DB_PASSWORD` desde el Secret |
| Actualización (productor) | `maxUnavailable: 0` y `maxSurge: 1`: no se retira un pod viejo hasta que el nuevo está listo |

## Exposición

| Service | Tipo | Acceso |
|---|---|---|
| `productor` | LoadBalancer | Único acceso público |
| `consumidor-inventario` | ClusterIP | Interno; se consulta con `kubectl port-forward svc/consumidor-inventario 8081:80` |
| `consumidor-notificacion` | ClusterIP | Interno |
| `kafka` | ClusterIP | Interno |

## HPA del inventario

Mínimo 1, máximo 3, objetivo 50 % de CPU. El máximo es 3 porque el tópico tiene 3 particiones: un cuarto consumidor del mismo grupo no recibiría ninguna.

## Verificar

kubectl get pods,svc,hpa
kubectl describe pod -l app=productor


## Limitaciones

Kafka usa un solo broker y disco efímero (el driver EBS no funciona en Learner Lab). Si el pod de Kafka se reinicia, se pierden los mensajes sin consumir y hay que recrear los tópicos.
'@ | Set-Content -Encoding utf8 k8s\README.md