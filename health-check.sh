#!/bin/bash
# Health Check Script for AI-SIEM
# Verifies all services are running and healthy

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "AI-SIEM Health Check"
echo "========================================"
echo ""

check_service() {
    local service=$1
    local url=$2
    local auth=$3
    
    echo -n "Checking $service... "
    
    if [ -n "$auth" ]; then
        response=$(curl -s -w "\n%{http_code}" -u "$auth" "$url" 2>/dev/null | tail -1)
    else
        response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null | tail -1)
    fi
    
    if [ "$response" = "200" ] || [ "$response" = "302" ]; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED (HTTP $response)${NC}"
        return 1
    fi
}

check_docker_service() {
    local container=$1
    
    echo -n "Checking Docker container $container... "
    
    if docker-compose ps "$container" | grep -q "Up"; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not running${NC}"
        return 1
    fi
}

# Check Docker containers
echo "Docker Services:"
check_docker_service "elasticsearch" || true
check_docker_service "kibana" || true
check_docker_service "logstash" || true
check_docker_service "grafana" || true
check_docker_service "redis" || true
check_docker_service "anomaly-detector" || true
check_docker_service "threat-detector" || true
check_docker_service "alerting-engine" || true

echo ""
echo "Web Services:"

# Check service endpoints
check_service "Elasticsearch" "http://localhost:9200/_cluster/health" "elastic:change_me_elastic_password" || true
check_service "Kibana" "http://localhost:5601/api/status" "" || true
check_service "Grafana" "http://localhost:3000/api/health" "" || true
check_service "Logstash" "http://localhost:9600" "" || true

echo ""
echo "Redis:"
echo -n "Checking Redis... "
if redis-cli -h localhost -p 6379 --raw incr ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connected${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
fi

echo ""
echo "Data:"
echo -n "Elasticsearch document count... "
count=$(curl -s -u elastic:change_me_elastic_password http://localhost:9200/siem-logs-*/_count | grep -o '"count":[0-9]*' | cut -d: -f2)
if [ -n "$count" ]; then
    echo -e "${GREEN}$count documents${NC}"
else
    echo -e "${YELLOW}Unable to retrieve${NC}"
fi

echo ""
echo "========================================"
echo "Health Check Complete"
echo "========================================"
