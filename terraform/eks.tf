# eks.tf
# Crea el clúster de Kubernetes administrado (EKS) y sus nodos.
# Adaptado a AWS Academy: NO se pueden crear roles IAM,
# por eso se reutiliza el rol existente "LabRole".
# ==========================================================

# ---------- 1. ROL DE PERMISOS ----------
# "data" = BUSCAR algo que ya existe (no crearlo).
# Aquí buscamos el rol LabRole que AWS Academy ya trae.
data "aws_iam_role" "lab" {
  name = "LabRole"
}

# ---------- 2. EL CLÚSTER (el "cerebro") ----------
resource "aws_eks_cluster" "this" {
  name     = var.cluster_name          # nombre; viene de variables.tf
  role_arn = data.aws_iam_role.lab.arn # permisos del clúster: LabRole
  version  = "1.31"                    # versión de Kubernetes

  vpc_config {
    # El clúster usa las subredes PRIVADAS (creadas en network.tf)
    subnet_ids = module.vpc.private_subnets

    # Endpoint público: puedo usar kubectl desde mi PC.
    # Los nodos siguen sin IP pública.
    endpoint_public_access  = true
    endpoint_private_access = true # los nodos hablan con el clúster por dentro de la VPC
  }

  # Da permisos de administrador a quien crea el clúster (yo),
  # para usar kubectl sin configuración extra.
  access_config {
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true
  }
}

# ---------- 3. LOS NODOS (las "máquinas") ----------
resource "aws_eks_node_group" "default" {
  cluster_name    = aws_eks_cluster.this.name  # los une al clúster de arriba
  node_group_name = "default"
  node_role_arn   = data.aws_iam_role.lab.arn  # mismo LabRole
  subnet_ids      = module.vpc.private_subnets # nodos SOLO en subredes privadas
  instance_types  = ["t3.medium"]              # 2 vCPU y 4 GB de RAM

  scaling_config {
    min_size     = 2 # mínimo 2: uno por zona de disponibilidad
    desired_size = 2 # arranca con 2
    max_size     = 3 # tope, para controlar el costo
  }
}

