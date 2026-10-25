# ecr.tf
# Registro de imágenes (ECR): el "almacén" donde se suben
# las imágenes Docker de los 3 servicios.

# "locals" = variable interna, solo vale dentro de este archivo.
locals {
  servicios = ["productor", "consumidor-inventario", "consumidor-notificacion"]
}

resource "aws_ecr_repository" "repos" {
  # for_each: crea UN repositorio por cada nombre de la lista.
  for_each = toset(local.servicios)
  name     = "agrolink/${each.key}" # ej.: agrolink/productor

  # IMMUTABLE: un tag NO se puede sobrescribir (trazabilidad).
  image_tag_mutability = "IMMUTABLE"

  # Permite "terraform destroy" aunque el repo tenga imágenes (punto 9).
  force_delete = true

  # Escanea vulnerabilidades en cada imagen que subes.
  image_scanning_configuration {
    scan_on_push = true
  }
}