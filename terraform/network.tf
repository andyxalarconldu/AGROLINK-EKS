# network.tf
# Construye la red: la VPC y sus subredes.
# Cumple punto 1: VPC con subredes públicas y privadas en 2 AZ.
# ==========================================================

# Un "module" es un paquete prearmado de la comunidad.
# Este crea VPC, subredes, rutas, Internet Gateway y NAT en un solo bloque
# (a mano serían unas 150 líneas).
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0" # versión fijada

  name = "agrolink-vpc"
  cidr = "10.0.0.0/16" # rango de IPs de toda la red (~65 mil direcciones)

  # Dos zonas de disponibilidad = dos centros de datos físicos distintos.
  # Si una cae, la otra sigue funcionando (alta disponibilidad).
  azs = ["us-east-1a", "us-east-1b"]

  # Subredes PÚBLICAS (una por zona): tienen salida directa a Internet.
  # Aquí irán el balanceador de carga y el NAT.
  public_subnets = ["10.0.1.0/24", "10.0.2.0/24"]

  # Subredes PRIVADAS (una por zona): SIN IP pública.
  # Aquí irán los nodos de Kubernetes y la base de datos.
  private_subnets = ["10.0.11.0/24", "10.0.12.0/24"]

  # NAT Gateway: permite que lo privado salga a Internet (por ejemplo,
  # para descargar imágenes) sin que nadie pueda entrar desde afuera.
  enable_nat_gateway = true

  # Un solo NAT para ahorrar costo (~USD 32/mes cada uno).
  # TRADE-OFF: es un punto único de falla. En producción: uno por zona.
  # (Menciónalo tú en la defensa antes de que pregunten.)
  single_nat_gateway = true

  enable_dns_hostnames = true # nombres DNS dentro de la VPC (necesario para EKS y RDS)

  # Etiquetas que Kubernetes lee para saber dónde crear balanceadores:
  # elb          = balanceadores públicos (en subredes públicas)
  # internal-elb = balanceadores internos (en subredes privadas)
  public_subnet_tags  = { "kubernetes.io/role/elb" = 1 }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = 1 }
}