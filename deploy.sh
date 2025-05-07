#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Production deployment script
function deploy() {
  echo -e "${BLUE}Deploying to production...${NC}"
  
  # Ensure production environment file exists
  if [ ! -f ".env.production" ]; then
    echo -e "${RED}ERROR: .env.production file not found. Please create it first.${NC}"
    exit 1
  fi
  
  # Check if Docker and Docker Compose are installed
  if ! command -v docker >/dev/null 2>&1 || ! command -v docker-compose >/dev/null 2>&1; then
    echo -e "${RED}ERROR: Docker and/or Docker Compose are not installed.${NC}"
    exit 1
  fi
  
  # Build production images
  echo -e "${YELLOW}Building production images...${NC}"
  docker-compose -f docker-compose.prod.yml build
  
  # Start production services
  echo -e "${YELLOW}Starting production services...${NC}"
  docker-compose -f docker-compose.prod.yml up -d
  
  echo -e "${GREEN}Deployment completed successfully!${NC}"
  echo -e "${YELLOW}API is now available at http://localhost:8000${NC}"
  echo -e "${YELLOW}View logs with: docker-compose -f docker-compose.prod.yml logs -f${NC}"
}

function stop() {
  echo -e "${BLUE}Stopping production services...${NC}"
  docker-compose -f docker-compose.prod.yml down
  echo -e "${GREEN}Production services stopped${NC}"
}

function backup_db() {
  echo -e "${BLUE}Backing up production database...${NC}"
  
  # Create backup directory if it doesn't exist
  mkdir -p ./backups
  
  # Get postgres container ID
  POSTGRES_CONTAINER=$(docker-compose -f docker-compose.prod.yml ps -q postgres)
  
  if [ -z "$POSTGRES_CONTAINER" ]; then
    echo -e "${RED}ERROR: Postgres container not found. Is it running?${NC}"
    exit 1
  fi
  
  # Generate backup filename with timestamp
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  BACKUP_FILE="./backups/medical_docs_backup_${TIMESTAMP}.sql"
  
  # Run pg_dump
  echo -e "${YELLOW}Creating database backup...${NC}"
  docker exec -it $POSTGRES_CONTAINER pg_dump -U postgres medical_docs > $BACKUP_FILE
  
  echo -e "${GREEN}Database backed up to: $BACKUP_FILE${NC}"
}

function restore_db() {
  echo -e "${BLUE}Restoring production database...${NC}"
  
  if [ -z "$1" ]; then
    echo -e "${RED}ERROR: No backup file specified.${NC}"
    echo -e "${YELLOW}Usage: ./deploy.sh restore_db ./backups/my_backup_file.sql${NC}"
    exit 1
  fi
  
  if [ ! -f "$1" ]; then
    echo -e "${RED}ERROR: Backup file $1 not found.${NC}"
    exit 1
  fi
  
  # Get postgres container ID
  POSTGRES_CONTAINER=$(docker-compose -f docker-compose.prod.yml ps -q postgres)
  
  if [ -z "$POSTGRES_CONTAINER" ]; then
    echo -e "${RED}ERROR: Postgres container not found. Is it running?${NC}"
    exit 1
  }
  
  # Restore database
  echo -e "${YELLOW}Restoring database from: $1${NC}"
  cat $1 | docker exec -i $POSTGRES_CONTAINER psql -U postgres -d medical_docs
  
  echo -e "${GREEN}Database restored successfully${NC}"
}

function show_help() {
  echo -e "${GREEN}Medical Document Analysis API - Production Deployment Script${NC}"
  echo -e "${YELLOW}Usage: ./deploy.sh <command>${NC}"
  echo ""
  echo "Commands:"
  echo "  deploy      - Deploy the application to production"
  echo "  stop        - Stop production services"
  echo "  backup_db   - Backup the production database"
  echo "  restore_db  - Restore the production database from a backup"
  echo "  help        - Show this help message"
}

# Command router
case "$1" in
  deploy)
    deploy
    ;;
  stop)
    stop
    ;;
  backup_db)
    backup_db
    ;;
  restore_db)
    restore_db $2
    ;;
  help|*)
    show_help
    ;;
esac 