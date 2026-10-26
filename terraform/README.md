@'
# terraform/ · Infraestructura como código

Crea en AWS toda la plataforma: red, clúster Kubernetes, base de datos y registro de imágenes. Son **28 recursos** definidos en 7 archivos, con estado remoto en S3 y versiones de proveedor fijadas.

## Archivos

| Archivo | Qué hace | Recursos |
|---|---|---|
| `versions.tf` | Versión de Terraform, proveedores y backend S3 del estado | 0 |
| `variables.tf` | Región (`us-east-1`) y nombre del clúster (`agrolink-eks`) | 0 |
| `network.tf` | VPC `10.0.0.0/16`, 2 subredes públicas, 2 privadas, Internet Gateway, NAT y rutas, mediante el módulo `terraform-aws-modules/vpc/aws` | 19 |
| `eks.tf` | Clúster EKS 1.31 y grupo de nodos 2 × t3.medium en subredes privadas | 2 |
| `rds.tf` | PostgreSQL 16 privada, subnet group, Security Group y contraseña aleatoria | 4 |
| `ecr.tf` | 3 repositorios inmutables con escaneo al subir | 3 |
| `outputs.tf` | Nombre del clúster, endpoint de RDS, contraseña (sensible) y URLs de ECR | 0 |
| `.terraform.lock.hcl` | Versiones exactas de los proveedores. **Debe versionarse** | |

## Decisiones de diseño

| Decisión | Razón |
|---|---|
| Estado remoto en S3 con versionado y `use_lockfile` | No depende de un equipo local y evita ejecuciones simultáneas |
| Proveedores `aws ~> 5.0` y `random ~> 3.6` | Versiones fijadas y reproducibles |
| Nodos y RDS en subredes privadas | Sin IP pública; la salida a Internet es por el NAT |
| SG de RDS con una sola regla: 5432 desde el SG del clúster | Ninguna regla abierta a `0.0.0.0/0` |
| Contraseña con `random_password` | Nunca aparece en el repositorio |
| `LabRole` en lugar de crear roles IAM | Learner Lab no permite crear roles |
| ECR `IMMUTABLE` y `force_delete` | Un tag por hash no se sobrescribe y el `destroy` funciona |
| Un solo NAT | Ahorro de costo; es un punto único de falla |

## Requisitos

Terraform 1.10 o superior, AWS CLI 2.x y credenciales vigentes del Learner Lab.

## Uso

El bucket del estado se crea una sola vez a mano, porque Terraform lo necesita antes de arrancar. El nombre debe ser único y coincidir con `versions.tf`:

aws s3api create-bucket --bucket NOMBRE-UNICO --region us-east-1
aws s3api put-bucket-versioning --bucket NOMBRE-UNICO --versioning-configuration Status=Enabled
aws s3api put-public-access-block --bucket NOMBRE-UNICO --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true


Luego:

terraform init
terraform validate
terraform plan
terraform apply


`apply` tarda de 15 a 20 minutos. Resultado esperado del plan completo: `Plan: 28 to add`.

## Salidas

terraform output -raw db_endpoint
terraform output -raw db_password
terraform output ecr_urls


`db_password` está marcada como sensible y no se imprime en el `apply`. No la captures ni la subas al repositorio.

## Reponer los nodos

Si la sesión del laboratorio expira y los nodos quedan `unreachable`:

terraform apply -replace="aws_eks_node_group.default"


## Destruir

Antes se borra el balanceador que creó Kubernetes (si no, la VPC no se puede eliminar):

kubectl delete -f ../k8s/02-productor.yaml
terraform destroy


Esperado: `Destroy complete! Resources: 28 destroyed.` El bucket del estado no lo gestiona Terraform y permanece.

## Notas

- `.terraform/` y los archivos `*.tfstate` no se versionan (ver `.gitignore`).
- Costo estimado de la infraestructura encendida: ~0,27 USD por hora.
'@ | Set-Content -Encoding utf8 terraform\README.md