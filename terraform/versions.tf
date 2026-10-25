# ==========================================================
# versions.tf
# Define: qué versión de Terraform uso, qué plugins necesito
# y DÓNDE guardo el estado (el "registro" de lo que creé).
# Cumple punto 1 del examen: estado remoto + versiones fijadas
# ==========================================================

terraform {
  # Exige Terraform 1.10 o superior.
  # Motivo: "use_lockfile" (bloqueo del estado en S3) solo existe desde 1.10.
  required_version = ">= 1.10.0"

  # Plugins (providers) que Terraform descarga.
  # "~> 5.0" significa: cualquier 5.x, pero NUNCA la 6.0.
  # Así fijo la versión y evito que una actualización rompa el código.
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }     # habla con AWS
    random = { source = "hashicorp/random", version = "~> 3.6" } # genera contraseñas
  }

  # Dónde se guarda el estado: en un bucket S3 (estado remoto).
  # Ventajas: no depende de mi PC, tiene versionado y bloqueo.
  backend "s3" {
    bucket       = "agrolink-tfstate-1003406285" # el bucket que creé a mano
    key          = "agrolink/terraform.tfstate"  # ruta del archivo dentro del bucket
    region       = "us-east-1"
    encrypt      = true # estado cifrado (contiene datos sensibles)
    use_lockfile = true # bloquea el estado mientras se ejecuta,
                        # evita que dos ejecuciones lo corrompan
  }
}

# Configuración del proveedor AWS.
provider "aws" {
  region = var.region # toma el valor de variables.tf

  # Etiquetas automáticas en TODOS los recursos creados.
  # Sirven para identificar de quién es cada recurso y sus costos.
  default_tags {
    tags = { Proyecto = "AgroLink", Caso = "2", Autor = "Alarcon" }
  }
}