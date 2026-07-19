output "alb_dns_name" {
  description = "A URL pública do Load Balancer para enviar requisições curl"
  value       = aws_alb.main.dns_name
}

output "database_endpoint" {
  description = "O endpoint interno do RDS PostgreSQL"
  value       = aws_db_instance.vector_db.endpoint
}