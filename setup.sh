#!/bin/bash
# Morolo Project Startup Script
# This script sets up and starts all services

set -e

echo "🚀 Starting Morolo Project Setup..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose are installed${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ .env file created. Please review and update with your OpenMetadata token if needed.${NC}"
    else
        echo -e "${RED}❌ .env.example not found!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env file exists${NC}"
fi
echo ""

# Pull latest images
echo -e "${YELLOW}📦 Pulling latest Docker images...${NC}"
docker-compose pull

echo ""
echo -e "${YELLOW}🐳 Starting Docker Compose services...${NC}"
docker-compose up -d

echo ""
echo -e "${YELLOW}⏳ Waiting for services to be healthy (this may take 1-2 minutes)...${NC}"

# Wait for backend to be healthy
max_attempts=60
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker-compose ps backend | grep -q "healthy"; then
        break
    fi
    attempt=$((attempt + 1))
    echo "  Attempt $attempt/$max_attempts... Backend not yet healthy"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}❌ Backend failed to become healthy after ${max_attempts} attempts${NC}"
    echo "Check logs with: docker-compose logs backend"
    exit 1
fi

echo -e "${GREEN}✅ Backend is healthy!${NC}"
echo ""

# Wait for other services
sleep 5

echo -e "${GREEN}✅ All services are running!${NC}"
echo ""
echo -e "${GREEN}🎉 Morolo is now ready!${NC}"
echo ""
echo "📋 Service URLs:"
echo "  🔵 FastAPI Docs:      http://localhost:8000/docs"
echo "  📊 OpenMetadata:      http://localhost:8585"
echo "  💾 MinIO Console:     http://localhost:9001"
echo "  🎨 Frontend:          http://localhost:3000"
echo ""
echo "📝 Next Steps:"
echo "  1. Open http://localhost:3000 in your browser"
echo "  2. Upload a test document to try PII detection"
echo "  3. Check http://localhost:8585 for OpenMetadata governance"
echo ""
echo "🔍 To view logs:"
echo "  docker-compose logs -f backend    # Backend logs"
echo "  docker-compose logs -f celery_worker  # Worker logs"
echo "  docker-compose ps                 # Service status"
echo ""
echo "🛑 To stop services:"
echo "  docker-compose down               # Stop all services"
echo "  docker-compose down -v            # Stop and remove volumes"
echo ""
