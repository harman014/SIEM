# Quick Reference Guide

## 🚀 Getting Started (5 minutes)

```bash
# 1. Navigate to project
cd /Users/ahmednaseem/Documents/Codex_Dev/AI-SIEM

# 2. Make scripts executable
bash setup-permissions.sh

# 3. Start all services
docker-compose up -d

# 4. Wait for services
sleep 30

# 5. Verify health
bash health-check.sh

# 6. Access interfaces
# Kibana:      http://localhost:5601 (elastic / password)
# Grafana:     http://localhost:3000 (admin / password)
# Elasticsearch: http://localhost:9200
```

## 📊 Testing the System (10 minutes)

```bash
# Generate full attack simulation
python3 sample-data/generate_logs.py --scenario full

# View dashboards
# Kibana Discover: http://localhost:5601/app/discover
# Grafana Dashboard: http://localhost:3000/dashboards

# Query results
python3 siem-client.py --command stats
python3 siem-client.py --command high-severity
```

## 🔧 Common Commands

### Service Management
```bash
# View status
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View specific service
docker-compose logs -f anomaly-detector

# Restart service
docker-compose restart elasticsearch

# Stop services
docker-compose stop

# Start services
docker-compose start
```

### Testing & Debugging
```bash
# Generate normal traffic
python3 sample-data/generate_logs.py --scenario normal --count 50

# Brute force test
python3 sample-data/generate_logs.py --scenario bruteforce --count 8

# DDoS test (10 seconds)
python3 sample-data/generate_logs.py --scenario ddos --count 10

# Check system health
bash health-check.sh

# Query alerts
python3 siem-client.py --command high-severity --hours 24
```

### Elasticsearch Management
```bash
# Cluster health
curl -u elastic:PASSWORD http://localhost:9200/_cluster/health?pretty

# Count documents
curl -u elastic:PASSWORD http://localhost:9200/siem-logs-*/_count

# List indices
curl -u elastic:PASSWORD http://localhost:9200/_cat/indices

# Delete old index
curl -X DELETE -u elastic:PASSWORD http://localhost:9200/siem-logs-2024.01.01
```

### Redis Operations
```bash
# Connect to Redis
docker exec -it ai-siem-redis redis-cli -a PASSWORD

# Check queue lengths
LLEN threats:queue
LLEN anomalies:queue

# View queue items
LRANGE threats:queue 0 -1

# Clear queue (careful!)
DEL threats:queue
```

## 📁 Project Structure

```
AI-SIEM/
├── docker-compose.yml          ← Main configuration
├── README.md                    ← Full documentation
├── DEPLOYMENT.md                ← Deployment guide
├── ARCHITECTURE.md              ← System architecture
├── TESTING.md                   ← Testing guide
├── quick-start.sh               ← Quick start script
├── health-check.sh              ← Health check script
├── setup-permissions.sh         ← Make scripts executable
├── siem-client.py               ← Python API client
│
├── elasticsearch/
│   ├── config/elasticsearch.yml
│   └── data/                    ← Persistent data
├── kibana/
│   └── config/kibana.yml
├── logstash/
│   ├── config/logstash.yml
│   └── pipeline/main.conf       ← Log processing rules
├── grafana/
│   ├── config/grafana.ini
│   ├── dashboards/              ← Security dashboards
│   └── provisioning/            ← Automated setup
│
├── anomaly-detection/           ← ML-based detection
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── threat-detection/            ← Pattern-based detection
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── alerting/                    ← Alert processing
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── config/alert_rules.yml
│
├── sample-data/
│   └── generate_logs.py         ← Test data generator
├── logs/                        ← Log input directory
└── redis/                       ← Redis data
```

## 🔑 Default Credentials

| Service | URL | Username | Password | Change In |
|---------|-----|----------|----------|-----------|
| Elasticsearch | localhost:9200 | elastic | change_me_elastic_password | docker-compose.yml |
| Kibana | localhost:5601 | elastic | (same as ES) | Auto-configured |
| Grafana | localhost:3000 | admin | change_me_grafana_password | docker-compose.yml |
| Redis | localhost:6379 | (none) | change_me_redis_password | docker-compose.yml |

⚠️ **IMPORTANT**: Change all credentials in `docker-compose.yml` before production use!

## 🎯 What Gets Detected

### Threat Detection Engine
- ✅ Brute force login attempts (5+ in 10 min)
- ✅ Port scanning (20+ ports in 5 min)
- ✅ DDoS attacks (1000+ req/min)
- ✅ Privilege escalation attempts
- ✅ Data exfiltration (>100MB/5min)
- ✅ Malware signatures

### Anomaly Detection Engine
- ✅ Unusual network traffic patterns
- ✅ Statistical outliers in packet rates
- ✅ Unexpected data transfer volumes
- ✅ Abnormal user behavior
- ✅ Deviations from baseline

## 📊 Monitoring Locations

| Metric | Location |
|--------|----------|
| Raw logs | Kibana Discover: localhost:5601/app/discover |
| Security dashboard | Grafana: localhost:3000/dashboards |
| Alerts | Kibana: localhost:5601/app/discover (siem-alerts-*) |
| Threats | Elasticsearch API or siem-client.py |
| Anomalies | Elasticsearch API or siem-client.py |
| Service logs | `docker-compose logs -f` |

## 🆘 Troubleshooting Quick Links

| Problem | Solution |
|---------|----------|
| Services won't start | Check: `docker-compose logs` and disk space |
| No data in Kibana | Verify: Send test event, check Logstash logs |
| Out of memory | Reduce: `ES_JAVA_OPTS` in docker-compose.yml |
| Can't login | Verify: Credentials match docker-compose.yml |
| Detection not working | Check: Logs in detection engine containers |
| High CPU/Memory | Reduce: `pipeline.batch.size` in Logstash |

## 📈 Performance Tips

### For SMB (up to 1M events/day):
- Current configuration is sufficient
- Monitor disk space weekly

### For Growth (1M-10M events/day):
```bash
# In docker-compose.yml:
ES_JAVA_OPTS: -Xms1g -Xmx1g          # Increase heap
pipeline.batch.size: 250              # Increase throughput
pipeline.workers: 4                   # Add workers
```

### For Large Scale (10M+ events/day):
- Use Elasticsearch cluster
- Add multiple Logstash instances
- Implement index sharding

## 🔐 Security Checklist

- [ ] Changed Elasticsearch password
- [ ] Changed Grafana admin password
- [ ] Changed Redis password
- [ ] Disabled external internet access
- [ ] Enabled HTTPS (optional)
- [ ] Set up network isolation
- [ ] Configured backup strategy
- [ ] Reviewed alerting rules

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| README.md | Full feature documentation |
| DEPLOYMENT.md | Step-by-step deployment guide |
| ARCHITECTURE.md | System design & data flow |
| TESTING.md | Complete testing guide |

## 🎓 Example Workflows

### Investigation Example:
```bash
# Alert comes in for high severity threat
# 1. Check Grafana dashboard → see spike in events
# 2. Go to Kibana → filter by source IP
# 3. Use siem-client.py → query related events
# 4. Review Elasticsearch timeline → determine pattern
# 5. Take action based on findings
```

### Tuning Example:
```bash
# Too many false positives in anomaly detection?
# 1. Check anomaly_detection/main.py
# 2. Increase contamination rate (default: 10%)
# 3. Adjust feature selection
# 4. Retrain with new data
# 5. Test with sample data
```

## 💡 Tips & Tricks

**Kibana Shortcuts:**
- Use KQL: `event_type:brute_force AND severity:high`
- Save searches for reuse
- Create visualizations from searches
- Set up alerts within Kibana

**Grafana Shortcuts:**
- Clone dashboards for variations
- Use variables for filtering
- Set auto-refresh (30s recommended)
- Share dashboards with read-only access

**Detection Tuning:**
- Adjust threat detection thresholds in `threat-detection/main.py`
- Modify anomaly features in `anomaly-detection/main.py`
- Configure alerting rules in `alerting/config/alert_rules.yml`

## 🤝 Support & Help

1. **Check logs**: `docker-compose logs -f <service>`
2. **Run health check**: `bash health-check.sh`
3. **Review documentation**: Check README.md, DEPLOYMENT.md
4. **Test system**: `python3 sample-data/generate_logs.py`
5. **Query API**: `python3 siem-client.py --command stats`

## 📞 Quick Start Contacts

- Elasticsearch: http://localhost:9200
- Kibana: http://localhost:5601
- Grafana: http://localhost:3000
- Logstash: localhost:5000 (TCP/UDP)

---

**Version**: 1.0.0  
**Last Updated**: December 2025  
**Status**: Production Ready
