# rds.tf
# Base de datos PostgreSQL de inventario.
# Cumple punto 7: no expuesta a Internet; solo accesible
# desde los nodos del clúster.
# Contraseña aleatoria de 20 caracteres.
# Nunca se escribe en el código: no queda en el repositorio (punto 3).
resource "random_password" "db" {
  length  = 20
  special = false # sin símbolos, para no romper la URL de conexión
}

# Le dice a RDS en qué subredes puede vivir: las PRIVADAS.
resource "aws_db_subnet_group" "db" {
  name       = "agrolink-db"
  subnet_ids = module.vpc.private_subnets
}

# Security Group = firewall de la base de datos.
resource "aws_security_group" "db" {
  name   = "agrolink-db-sg"
  vpc_id = module.vpc.vpc_id

  # ÚNICA regla de entrada: PostgreSQL (5432) desde el SG del clúster.
  # El origen es OTRO security group, no un rango de IPs: solo los nodos
  # pueden conectarse. No existe ninguna regla 0.0.0.0/0.
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_eks_cluster.this.vpc_config[0].cluster_security_group_id]
  }
}

# La base de datos en sí.
resource "aws_db_instance" "inventario" {
  identifier        = "agrolink-inventario"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = "db.t3.micro" # la más pequeña (ahorro)
  allocated_storage = 20            # GB

  db_name  = "inventario"
  username = "agrolink"
  password = random_password.db.result # la contraseña generada arriba

  db_subnet_group_name   = aws_db_subnet_group.db.name # subredes privadas
  vpc_security_group_ids = [aws_security_group.db.id]  # el firewall de arriba

  publicly_accessible = false # SIN IP pública (refuerza punto 7)
  storage_encrypted   = true  # disco cifrado
  skip_final_snapshot = true  # sin copia final: permite destroy limpio
}