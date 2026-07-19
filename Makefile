.PHONY: up down status open-ui help

# Terminal Colors
GREEN=\033[0;32m
CYAN=\033[0;36m
YELLOW=\033[1;33m
NC=\033[0m # No Color

help:
	@echo -e "${CYAN}===================================================${NC}"
	@echo -e "${GREEN}    AIOps Platform - LLM SRE Agent${NC}"
	@echo -e "${CYAN}===================================================${NC}"
	@echo -e "Available commands:"
	@echo -e "  ${YELLOW}make up${NC}       - Spin up all simulated infrastructure (API, DB, Grafana, Loki)"
	@echo -e "  ${YELLOW}make down${NC}     - Tear down the infrastructure"
	@echo -e "  ${YELLOW}make open-ui${NC}  - Display links and open UIs in the default browser"
	@echo -e "  ${YELLOW}make seed${NC}     - Populate/reload the SRE manual in the Vector Database"
	@echo -e "  ${YELLOW}make status${NC}   - Show status of the running containers"
	@echo -e "${CYAN}===================================================${NC}"

up:
	@echo -e "${CYAN}Starting Virtual SRE infrastructure (Mocked)...${NC}"
	docker compose up -d
	@echo -e "${GREEN}Infrastructure is up and running!${NC}"
	@$(MAKE) seed
	@$(MAKE) open-ui

down:
	@echo -e "${YELLOW}Tearing down the infrastructure...${NC}"
	docker compose down

seed:
	@echo -e "${YELLOW}Waiting for the API to initialize (Downloading AI Models can take up to 2 mins)...${NC}"
	@for i in $$(seq 1 30); do \
		if curl -s http://localhost:8000/docs > /dev/null; then \
			break; \
		fi; \
		sleep 5; \
	done
	@echo -e "${CYAN}Feeding the Knowledge Base (Vector DB)...${NC}"
	@for file in docs/*.md; do \
		echo -e "${CYAN}Ingesting $$file...${NC}"; \
		curl -s -X POST "http://localhost:8000/upload_document" \
			-H "accept: application/json" \
			-H "Content-Type: multipart/form-data" \
			-F "file=@$$file" > /dev/null; \
	done
	@echo -e "${GREEN}All SRE Manuals successfully injected into the AI memory!${NC}"

open-ui:
	@echo -e "${CYAN}===================================================${NC}"
	@echo -e "${GREEN} Platform Quick Access Links (Mocked):${NC}"
	@echo -e "  API (FastAPI)     : http://localhost:8000/docs"
	@echo -e "  Grafana (Metrics) : http://localhost:3000 (admin/admin)"
	@echo -e "  Prometheus        : http://localhost:9090"
	@echo -e "  Loki (Logs)       : http://localhost:3100"
	@echo -e "${CYAN}===================================================${NC}"
	@echo -e "Opening tabs in your default browser..."
	@python3 -c "import webbrowser; webbrowser.open('http://localhost:8000/docs'); webbrowser.open('http://localhost:3000')" 2>/dev/null || echo "Could not open automatically, please click the links above."

status:
	docker compose ps
