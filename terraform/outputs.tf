# outputs.tf
# Datos que Terraform muestra al terminar y que usaremos
# luego (conectar apps a la BD y subir imágenes a ECR).
output "cluster_name" {
  value = aws_eks_cluster.this.name
}

# Dirección (host) de la BD, para que las apps se conecten.
output "db_endpoint" {
  value = aws_db_instance.inventario.address
}

# sensitive = true: no se imprime en pantalla por seguridad.
# Se consulta con: terraform output -raw db_password
output "db_password" {
  value     = random_password.db.result
  sensitive = true
}

# URLs de los 3 repositorios, para hacer docker push.
output "ecr_urls" {
  value = { for k, r in aws_ecr_repository.repos : k => r.repository_url }
}