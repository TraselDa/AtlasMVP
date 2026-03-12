# ===========================================
# AtlasMVP - Makefile Principal
# ===========================================

.PHONY: help secrets-encrypt secrets-decrypt secrets-list secrets-key secrets-status \
        dev qa prod stop logs status \
        backend-dev backend-qa backend-prod \
        llm-dev llm-qa llm-prod \
        clean network

# Colors
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
BLUE = \033[0;34m
NC = \033[0m

# Scripts
SECRETS_SCRIPT = ./scripts/secrets.sh

# Docker compose paths
BACKEND_COMPOSE_DEV = -f backend/infra/backend/docker-compose-dev.yml
BACKEND_COMPOSE_QA = -f backend/infra/backend/docker-compose-qa.yml
BACKEND_COMPOSE_PROD = -f backend/infra/backend/docker-compose-prod.yml

DB_COMPOSE = -f backend/infra/db/docker-compose.yml

LLM_COMPOSE_DEV = -f llm_core/docker-compose-dev.yml
LLM_COMPOSE_QA = -f llm_core/docker-compose-qa.yml
LLM_COMPOSE_PROD = -f llm_core/docker-compose-prod.yml

help: ## Affiche cette aide
	@echo ""
	@echo "$(GREEN)AtlasMVP - Commandes disponibles$(NC)"
	@echo "=================================="
	@echo ""
	@echo "$(BLUE)=== Secrets (chiffrement) ===$(NC)"
	@grep -E '^secrets-[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BLUE)=== Environnements complets ===$(NC)"
	@echo "$(YELLOW)dev$(NC)                  Démarre tout l'environnement DEV"
	@echo "$(YELLOW)qa$(NC)                   Démarre tout l'environnement QA"
	@echo "$(YELLOW)prod$(NC)                 Démarre tout l'environnement PROD"
	@echo "$(YELLOW)stop$(NC)                 Arrête tous les conteneurs"
	@echo ""
	@echo "$(BLUE)=== Services individuels ===$(NC)"
	@echo "$(YELLOW)db-up$(NC)                Infrastructure DB (Mongo, MinIO, Chroma)"
	@echo "$(YELLOW)backend-dev$(NC)          Backend DEV uniquement"
	@echo "$(YELLOW)llm-dev$(NC)              LLM Core DEV uniquement"
	@echo ""
	@echo "$(BLUE)=== Utilitaires ===$(NC)"
	@echo "$(YELLOW)logs$(NC)                 Logs de tous les conteneurs"
	@echo "$(YELLOW)status$(NC)               Statut des conteneurs"
	@echo "$(YELLOW)network$(NC)              Créer le réseau Docker"
	@echo "$(YELLOW)clean$(NC)                Nettoyer tous les conteneurs"
	@echo ""

# ===========================================
# Gestion des secrets
# ===========================================

secrets-key: ## Génère la clé de chiffrement (une seule fois)
	@$(SECRETS_SCRIPT) generate-key

secrets-encrypt: ## Chiffre tous les fichiers .env
	@$(SECRETS_SCRIPT) encrypt

secrets-decrypt: ## Déchiffre tous les fichiers .env
	@$(SECRETS_SCRIPT) decrypt

secrets-list: ## Liste les fichiers et leur statut
	@$(SECRETS_SCRIPT) list

secrets-status: secrets-list ## Alias pour secrets-list

secrets-clean: ## Supprime les fichiers .env en clair
	@$(SECRETS_SCRIPT) clean

# ===========================================
# Environnements complets (avec déchiffrement)
# ===========================================

dev: secrets-decrypt network ## Démarre l'environnement DEV complet
	@echo "$(GREEN)Démarrage de l'environnement DEV...$(NC)"
	@make db-up
	@make backend-dev
	@make llm-dev
	@echo ""
	@echo "$(GREEN)Environnement DEV démarré!$(NC)"
	@echo "  Backend:       http://localhost:8020"
	@echo "  LLM Core:      http://localhost:8030"

qa: secrets-decrypt network ## Démarre l'environnement QA complet
	@echo "$(GREEN)Démarrage de l'environnement QA...$(NC)"
	@make db-up
	@make backend-qa
	@make llm-qa
	@echo ""
	@echo "$(GREEN)Environnement QA démarré!$(NC)"

prod: secrets-decrypt network ## Démarre l'environnement PROD complet
	@echo "$(GREEN)Démarrage de l'environnement PROD...$(NC)"
	@make db-up
	@make backend-prod
	@make llm-prod
	@echo ""
	@echo "$(GREEN)Environnement PROD démarré!$(NC)"

stop: ## Arrête tous les conteneurs
	@echo "$(YELLOW)Arrêt de tous les conteneurs...$(NC)"
	-docker compose $(DB_COMPOSE) down 2>/dev/null
	-docker compose $(BACKEND_COMPOSE_DEV) down 2>/dev/null
	-docker compose $(BACKEND_COMPOSE_QA) down 2>/dev/null
	-docker compose $(BACKEND_COMPOSE_PROD) down 2>/dev/null
	-docker compose $(LLM_COMPOSE_DEV) down 2>/dev/null
	-docker compose $(LLM_COMPOSE_QA) down 2>/dev/null
	-docker compose $(LLM_COMPOSE_PROD) down 2>/dev/null
	@echo "$(GREEN)Tous les conteneurs arrêtés.$(NC)"

# ===========================================
# Services individuels
# ===========================================

# Base de données & Infra
db-up: ## Démarre l'infrastructure DB
	@echo "$(GREEN)Démarrage de l'infrastructure DB...$(NC)"
	docker compose $(DB_COMPOSE) up -d

db-down: ## Arrête l'infrastructure DB
	-docker compose $(DB_COMPOSE) down 2>/dev/null

# Backend
backend-dev: ## Démarre le backend DEV
	@echo "$(GREEN)Démarrage du backend DEV...$(NC)"
	docker compose $(BACKEND_COMPOSE_DEV) up -d

backend-qa: ## Démarre le backend QA
	@echo "$(GREEN)Démarrage du backend QA...$(NC)"
	docker compose $(BACKEND_COMPOSE_QA) up -d

backend-prod: ## Démarre le backend PROD
	@echo "$(GREEN)Démarrage du backend PROD...$(NC)"
	docker compose $(BACKEND_COMPOSE_PROD) up -d

backend-down: ## Arrête le backend
	-docker compose $(BACKEND_COMPOSE_DEV) down 2>/dev/null
	-docker compose $(BACKEND_COMPOSE_QA) down 2>/dev/null
	-docker compose $(BACKEND_COMPOSE_PROD) down 2>/dev/null

# LLM Core
llm-dev: ## Démarre LLM Core DEV
	@echo "$(GREEN)Démarrage de LLM Core DEV...$(NC)"
	docker compose $(LLM_COMPOSE_DEV) up -d

llm-qa: ## Démarre LLM Core QA
	@echo "$(GREEN)Démarrage de LLM Core QA...$(NC)"
	docker compose $(LLM_COMPOSE_QA) up -d

llm-prod: ## Démarre LLM Core PROD
	@echo "$(GREEN)Démarrage de LLM Core PROD...$(NC)"
	docker compose $(LLM_COMPOSE_PROD) up -d

llm-down: ## Arrête LLM Core
	-docker compose $(LLM_COMPOSE_DEV) down 2>/dev/null
	-docker compose $(LLM_COMPOSE_QA) down 2>/dev/null
	-docker compose $(LLM_COMPOSE_PROD) down 2>/dev/null

# ===========================================
# Utilitaires
# ===========================================

logs: ## Affiche les logs de tous les conteneurs
	docker ps --format "{{.Names}}" | xargs -I {} docker logs -f {} &

status: ## Affiche le statut des conteneurs
	@echo "$(GREEN)Conteneurs en cours d'exécution:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

network: ## Crée le réseau Docker atlas-net
	@docker network inspect atlas-net >/dev/null 2>&1 || \
		(docker network create atlas-net && echo "$(GREEN)Réseau atlas-net créé$(NC)")

clean: stop ## Arrête et supprime tous les conteneurs et volumes
	@echo "$(RED)Nettoyage complet...$(NC)"
	-docker compose $(DB_COMPOSE) down -v 2>/dev/null
	-docker compose $(BACKEND_COMPOSE_DEV) down -v 2>/dev/null
	-docker compose $(LLM_COMPOSE_DEV) down -v 2>/dev/null
	@echo "$(GREEN)Nettoyage terminé.$(NC)"
