
# ==============================================================================
# 4. DATA STORE LAYER (Vector Database on AWS RDS PostgreSQL)
# ==============================================================================
resource "aws_db_subnet_group" "db_subnets" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "vector_db" {
  identifier             = "${var.project_name}-vector-db"
  allocated_storage      = 20
  max_allocated_storage  = 100 # Auto-scaling do disco do banco vetorial
  engine                 = "postgres"
  engine_version         = "16.1" # Versão moderna estável com suporte nativo ao pgvector
  instance_class         = "db.t4g.micro" # Instância de baixo custo com processador Graviton
  db_name                = "sre_vector_manual"
  username               = "db_admin"
  password               = "SRE_Super_Secure_Pass_2026!" # Em produção real, use o AWS Secrets Manager
  db_subnet_group_name   = aws_db_subnet_group.db_subnets.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = true
}

# ==============================================================================
# 5. COMPUTE & ORCHESTRATION LAYER (ECS Serverless Cluster & Load Balancer)
# ==============================================================================
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"
}

# CloudWatch Logs para Observabilidade da Aplicação
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "app" {
  family                   = var.project_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"  # 0.5 vCPU
  memory                   = "1024" # 1 GB RAM
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "api-agent-container"
      image     = "nginx:latest" # Placeholder. O seu CI/CD irá sobrescrever isso com a sua imagem real do Python.
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
        }
      ]
      environment = [
        { name = "ENVIRONMENT", value = "production" },
        { name = "AWS_DEFAULT_REGION", value = var.aws_region },
        { name = "DB_HOST", value = aws_db_instance.vector_db.address },
        { name = "DB_NAME", value = aws_db_instance.vector_db.db_name },
        { name = "DB_USER", value = aws_db_instance.vector_db.username }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "app"
        }
      }
    }
  ])
}

# Application Load Balancer (ALB)
resource "aws_alb" "main" {
  name            = "${var.project_name}-alb"
  subnets         = aws_subnet.public[*].id
  security_groups = [aws_security_group.alb.id]
}

resource "aws_alb_target_group" "app" {
  name        = "${var.project_name}-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  # BOAS PRÁTICAS DE SRE: Health Check customizado para lidar com o warm-up da API de IA
  health_check {
    healthy_threshold   = "3"
    interval            = "30"
    protocol            = "HTTP"
    matcher             = "200"
    timeout             = "5"
    path                = "/health" # Endpoint que criaremos na API Python
    unhealthy_threshold = "5"
  }
}

resource "aws_alb_listener" "http" {
  load_balancer_arn = aws_alb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    target_group_arn = aws_alb_target_group.app.arn
    type             = "forward"
  }
}

# ECS Service (Gerencia e mantém os containers rodando estavelmente)
resource "aws_ecs_service" "main" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 2 # Alta disponibilidade: Mantém sempre 2 réplicas rodando
  launch_type     = "FARGATE"

  network_configuration {
    security_groups = [aws_security_group.app.id]
    subnets         = aws_subnet.private[*].id
  }

  load_balancer {
    target_group_arn = aws_alb_target_group.app.arn
    container_name   = "api-agent-container"
    container_port   = 8000
  }

  depends_on = [aws_alb_listener.http]
}
