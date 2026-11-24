# Deployment Guide - AI-SIEM

## Prerequisites

- Docker and Docker Compose installed
- 4+ GB RAM available
- 20+ GB free disk space
- macOS, Linux, or Windows with Docker Desktop
- Basic understanding of terminal/command line

## Step-by-Step Deployment

### Step 1: Prepare System

```bash
# Navigate to project directory
cd /Users/ahmednaseem/Documents/Codex_Dev/AI-SIEM

# Create required data directories
mkdir -p elasticsearch/data redis/data logs sample-data

# Set permissions (Linux/macOS)
chmod 755 elasticsearch/data redis/data logs sample-data
```

### Step 2: Configure Credentials

Edit `docker-compose.yml` and update these critical passwords:

```yaml
# Find and update:
- ELASTIC_PASSWORD=your_secure_password       # Change from: change_me_elastic_password
- GF_SECURITY_ADMIN_PASSWORD=your_password    # Change from: change_me_grafana_password
- redis password in command                   # Change from: change_me_redis_password
```

Also update in configuration files:
- `kibana/config/kibana.yml`: `elasticsearch.password`
- `logstash/config/logstash.yml`: If configured
- `grafana/provisioning/datasources/elasticsearch.yml`: `basicAuthPassword`

### Step 3: Start Services

```bash
# Start all services in background
docker-compose up -d

# Wait 30 seconds for services to initialize
sleep 30

# Verify all services are running
docker-compose ps
```

Expected output:
```
NAME                    STATUS
ai-siem-elasticsearch   Up (healthy)
ai-siem-kibana         Up (healthy)
ai-siem-logstash       Up (healthy)
ai-siem-grafana        Up (healthy)
ai-siem-redis          Up (healthy)
ai-siem-anomaly-detector  Up
ai-siem-threat-detector    Up
ai-siem-alerting           Up
```

### Step 4: Verify Connectivity

```bash
# Test Elasticsearch
curl -u elastic:your_password http://localhost:9200/_cluster/health

# Test Kibana (should return 200)
curl http://localhost:5601/api/status

# Test Grafana
curl http://localhost:3000/api/health
```

### Step 5: Access Web Interfaces

1. **Kibana** (Log Analysis):
   - URL: http://localhost:5601
   - Username: `elastic`
   - Password: Your Elasticsearch password

2. **Grafana** (Dashboards):
   - URL: http://localhost:3000
   - Username: `admin`
   - Password: Your Grafana password
   - First login will prompt to change password

3. **Elasticsearch** (API):
   - URL: http://localhost:9200
   - Auth: Basic auth with elastic credentials

## Sending Test Data

### Option 1: Manual JSON via Netcat

```bash
# Single event
echo '{"event_type":"connection_attempt","src_ip":"192.168.1.100","dst_ip":"8.8.8.8","src_port":54321,"dst_port":443,"packet_count":10,"byte_count":1024}' | nc localhost 5000

# Brute force simulation (5+ failed logins in 10 min)
for i in {1..6}; do
  echo "{\"event_type\":\"authentication_failed\",\"src_ip\":\"192.168.1.50\",\"dst_ip\":\"10.0.0.5\",\"user\":\"admin\"}" | nc localhost 5000
  sleep 2
done
```

### Option 2: Use Sample Log Generator

Create `test_data_generator.py`:

```python
#!/usr/bin/env python3
import socket
import json
import time
import random

def send_log(event):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', 5000))
    sock.sendall((json.dumps(event) + '\n').encode())
    sock.close()

# Generate test events
for i in range(100):
    event = {
        "event_type": random.choice(["connection_attempt", "authentication_failed", "data_transfer"]),
        "src_ip": f"192.168.1.{random.randint(1, 254)}",
        "dst_ip": f"10.0.0.{random.randint(1, 254)}",
        "src_port": random.randint(1024, 65535),
        "dst_port": random.choice([22, 80, 443, 3306, 5432]),
        "packet_count": random.randint(1, 1000),
        "byte_count": random.randint(100, 100000),
        "severity": random.choice(["low", "medium", "high", "critical"])
    }
    send_log(event)
    time.sleep(0.5)
    print(f"Sent event {i+1}/100")
```

Run it:
```bash
python3 test_data_generator.py
```

## Post-Deployment Configuration

### 1. Set Elasticsearch Index Lifecycle

```bash
# Create index template with 30-day retention
curl -X PUT http://localhost:9200/_ilm/policy/siem-policy \
  -H 'Content-Type: application/json' \
  -u elastic:your_password \
  -d '{
    "policy": {
      "phases": {
        "hot": {"min_age": "0d", "actions": {}},
        "delete": {"min_age": "30d", "actions": {"delete": {}}}
      }
    }
  }'
```

### 2. Configure Grafana Data Source

If not auto-provisioned:
1. Go to http://localhost:3000/datasources
2. Click "Add data source"
3. Select "Elasticsearch"
4. Set URL: `http://elasticsearch:9200`
5. Auth: Basic, Username: `elastic`, Password: your_password
6. Index name: `siem-logs-*`
7. Time field name: `@timestamp`
8. Click "Save & Test"

### 3. Import Grafana Dashboard

```bash
# If dashboard didn't auto-import, import manually:
# 1. Go to http://localhost:3000/dashboards
# 2. Click "New" → "Import"
# 3. Paste dashboard JSON from grafana/dashboards/security-overview.json
```

### 4. Configure Log Source Integration

**For Filebeat-based systems** (Linux/macOS):

```yaml
# /etc/filebeat/filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/auth.log
    - /var/log/syslog
    - /var/log/apache2/access.log

output.logstash:
  hosts: ["your-siem-server.com:5000"]
```

**For Syslog-based systems**:

Configure syslog on remote devices:
```
*.* @your-siem-server.com:5000
```

## Monitoring & Health Checks

### View Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f anomaly-detector
docker-compose logs -f threat-detector
docker-compose logs -f alerting-engine
docker-compose logs -f logstash

# Last 100 lines
docker-compose logs --tail 100
```

### Check Service Health

```bash
# Status of all containers
docker-compose ps

# Detailed info on specific service
docker inspect ai-siem-elasticsearch

# View container resource usage
docker stats
```

### Elasticsearch Cluster Health

```bash
curl -u elastic:your_password http://localhost:9200/_cluster/health?pretty
```

Response should show:
```json
{
  "cluster_name" : "ai-siem-cluster",
  "status" : "green",
  "number_of_nodes" : 1
}
```

### Count Indexed Documents

```bash
curl -u elastic:your_password http://localhost:9200/siem-logs-*/_count
```

## Troubleshooting Deployment

### Service Won't Start

```bash
# Check logs
docker-compose logs <service_name>

# Common issue: Port in use
lsof -i :9200        # Check Elasticsearch port
lsof -i :5601        # Check Kibana port

# Solution: Kill process or change port in docker-compose.yml
```

### Elasticsearch Health Issues

```bash
# Check cluster status
curl -u elastic:your_password http://localhost:9200/_cluster/stats

# Check node status
curl -u elastic:your_password http://localhost:9200/_nodes/stats

# Restart Elasticsearch
docker-compose restart elasticsearch
```

### No Data Appearing in Kibana

```bash
# 1. Verify data was indexed
curl -u elastic:your_password http://localhost:9200/siem-logs-*/_count

# 2. Check Logstash pipeline
docker-compose logs logstash | grep -i error

# 3. Check if logs are being sent
netstat -an | grep 5000    # Check port listening

# 4. Verify log format
echo '{"test":"data"}' | nc localhost 5000
```

### Memory Issues

If services crash due to memory:

```yaml
# Edit docker-compose.yml - reduce heap sizes:
ES_JAVA_OPTS: -Xms256m -Xmx256m  # Reduced from 512m
```

Then restart:
```bash
docker-compose up -d
```

## Stopping & Restarting

```bash
# Stop all services (keeps data)
docker-compose stop

# Start services
docker-compose start

# Full restart
docker-compose restart

# Stop and remove containers (keeps volumes/data)
docker-compose down

# Complete cleanup (removes everything including volumes!)
docker-compose down -v
```

## Upgrading Components

### Update Service Images

```bash
# Pull latest images
docker-compose pull

# Restart services
docker-compose up -d
```

### Backup Data Before Upgrade

```bash
# Backup Elasticsearch data
tar -czf elasticsearch-backup.tar.gz elasticsearch/data/

# Backup Grafana
docker exec ai-siem-grafana grafana-cli admin export-dashboard > dashboards-backup.json
```

## Production Considerations

### 1. Security

```bash
# Change all default credentials
# Implement network policies
# Use HTTPS with certificates
# Enable Elasticsearch security features
```

### 2. Backup Strategy

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/mnt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Elasticsearch snapshot
curl -X PUT "http://localhost:9200/_snapshot/backup-repo" \
  -H 'Content-Type: application/json' \
  -d "{ \"type\": \"fs\", \"settings\": { \"location\": \"$BACKUP_DIR/elasticsearch\" } }"
```

### 3. Monitoring

```bash
# Set up external monitoring
# - Monitor disk space
# - Monitor memory usage
# - Monitor network traffic
# - Set up alerts for service failures
```

### 4. Log Retention

```bash
# Implement ILM policy for automatic deletion
# Monitor index size growth
# Archive old indices
```

## Performance Tuning

### For 10M+ events/day

```yaml
# docker-compose.yml
elasticsearch:
  environment:
    - ES_JAVA_OPTS=-Xms2g -Xmx2g

logstash:
  environment:
    - LS_JAVA_OPTS=-Xmx1g -Xms1g
```

### Enable persistent queue in Logstash

```conf
# logstash/config/logstash.yml
queue.type: persisted
queue.max_bytes: 1gb
```

---

**Need Help?** Check service logs and Elasticsearch health status first.
