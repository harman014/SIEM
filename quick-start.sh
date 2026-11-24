#!/bin/bash
# Quick start script for AI-SIEM

set -e

echo "======================================"
echo "AI-SIEM Quick Start"
echo "======================================"
echo ""

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed"
    exit 1
fi

# Create required directories
echo "📁 Creating data directories..."
mkdir -p elasticsearch/data redis/data logs sample-data
chmod 755 elasticsearch/data redis/data logs sample-data 2>/dev/null || true

echo ""
echo "⚠️  Please update credentials in docker-compose.yml:"
echo "   - ELASTIC_PASSWORD"
echo "   - GF_SECURITY_ADMIN_PASSWORD"
echo "   - REDIS password"
echo ""
read -p "Have you updated the credentials? (yes/no) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please edit docker-compose.yml first"
    exit 1
fi

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 30

echo ""
echo "✓ Services started!"
echo ""
echo "📊 Access your SIEM:"
echo "   Kibana:      http://localhost:5601"
echo "   Grafana:     http://localhost:3000"
echo "   Elasticsearch: http://localhost:9200"
echo ""
echo "🧪 Generate test data:"
echo "   python3 sample-data/generate_logs.py --scenario full"
echo ""
echo "📋 Check status:"
echo "   docker-compose ps"
echo "   bash health-check.sh"
echo ""
echo "📖 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose stop"
echo ""
