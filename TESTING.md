# Testing Guide - AI-SIEM

## Test Environment Setup

### Prerequisites

- All services running (`docker-compose ps` shows all "Up")
- Python 3.7+ for test scripts
- netcat or nc command for manual testing
- curl for API testing

## Automated Testing

### 1. Full Scenario Test

Generates a complete attack simulation with normal baseline and multiple attack patterns:

```bash
# Make script executable
chmod +x sample-data/generate_logs.py

# Run full test scenario
python3 sample-data/generate_logs.py --scenario full

# Monitor detection in real-time
docker-compose logs -f anomaly-detector
docker-compose logs -f threat-detector
docker-compose logs -f alerting-engine
```

**Timeline**:
- 0-10s: Normal traffic baseline (50 events)
- 10-15s: Brute force attack (8 failed logins)
- 15-30s: Port scanning (25 ports)
- 30-35s: Data exfiltration (3 events)
- 35-40s: DDoS attack (100+ requests)
- 40-45s: Privilege escalation (2 attempts)

**Expected Detections**:
- ✅ Brute force alert (HIGH)
- ✅ Port scan alert (MEDIUM)
- ✅ Data exfil alert (CRITICAL)
- ✅ DDoS alert (CRITICAL)
- ✅ Privilege escalation alert (CRITICAL)
- ✅ Multiple anomalies detected

### 2. Individual Scenario Tests

Test specific attack patterns in isolation:

```bash
# Test 1: Normal traffic baseline
python3 sample-data/generate_logs.py --scenario normal --count 50

# Test 2: Brute force attack
python3 sample-data/generate_logs.py --scenario bruteforce --count 8

# Test 3: Port scanning
python3 sample-data/generate_logs.py --scenario portscan --count 30

# Test 4: DDoS simulation (10 second duration)
python3 sample-data/generate_logs.py --scenario ddos --count 10

# Test 5: Data exfiltration
python3 sample-data/generate_logs.py --scenario exfil --count 5

# Test 6: Privilege escalation
python3 sample-data/generate_logs.py --scenario escalation --count 3
```

## Manual Testing

### Test 1: Send Single Event via Netcat

```bash
# Normal connection event
echo '{"event_type":"connection_attempt","src_ip":"192.168.1.100","dst_ip":"8.8.8.8","src_port":54321,"dst_port":443,"packet_count":10,"byte_count":1024,"severity":"low"}' | nc localhost 5000

# Verify in Kibana
# Navigate to: http://localhost:5601/app/discover
# Search: event_type:connection_attempt
```

### Test 2: Verify Logstash Processing

```bash
# Check Logstash status
curl http://localhost:9600

# View Logstash logs
docker-compose logs logstash | tail -20

# Expected output: "Received event" and successful indexing
```

### Test 3: Query Elasticsearch Directly

```bash
# Get cluster health
curl -u elastic:change_me_elastic_password http://localhost:9200/_cluster/health?pretty

# Count documents
curl -u elastic:change_me_elastic_password http://localhost:9200/siem-logs-*/_count

# Search recent events
curl -u elastic:change_me_elastic_password http://localhost:9200/siem-logs-*/_search?pretty \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {"match_all": {}},
    "size": 10,
    "sort": [{"@timestamp": {"order": "desc"}}]
  }'
```

### Test 4: Check Redis Queue

```bash
# Connect to Redis
docker exec -it ai-siem-redis redis-cli -a change_me_redis_password

# Check queue length
LLEN threats:queue
LLEN anomalies:queue
LLEN alerts:queue

# Peek at queue items
LRANGE threats:queue 0 -1
LRANGE anomalies:queue 0 -1

# Exit
exit
```

### Test 5: Verify Detection Engines

```bash
# Check anomaly detector logs
docker-compose logs anomaly-detector | tail -50

# Check threat detector logs
docker-compose logs threat-detector | tail -50

# Check alerting engine logs
docker-compose logs alerting-engine | tail -50

# Look for: "Detected" and "Published" messages
```

## Web Interface Testing

### Kibana Testing

1. **Access Kibana**:
   - URL: http://localhost:5601
   - Username: `elastic`
   - Password: your Elasticsearch password

2. **Create Index Pattern**:
   - Go to Management → Index Patterns
   - Create pattern: `siem-logs-*`
   - Time field: `@timestamp`

3. **Discover Logs**:
   - Go to Discover
   - Select index: `siem-logs-*`
   - Filter: `event_type:"authentication_failed"`
   - Expected: 0 results (initially)

4. **After running tests**:
   - Run brute force test
   - Refresh Discover
   - Expected: Multiple failed auth events visible

### Grafana Testing

1. **Access Grafana**:
   - URL: http://localhost:3000
   - Username: `admin`
   - Password: your Grafana password

2. **Import Dashboard**:
   - Left menu → Dashboards → Import
   - Upload: `grafana/dashboards/security-overview.json`
   - Select Elasticsearch datasource

3. **View Dashboard**:
   - Should show 4 panels
   - All panels initially empty (no data)

4. **After running tests**:
   - Refresh dashboard
   - Expected to see:
     - Event timeline with spike
     - High severity event count increase
     - Event distribution by type
     - Severity breakdown

## API Testing

### Using SIEM Client

```bash
# Make executable
chmod +x siem-client.py

# Get system statistics
python3 siem-client.py --command stats

# Get recent alerts (last 24 hours)
python3 siem-client.py --command alerts --hours 24

# Get detected threats
python3 siem-client.py --command threats --hours 24

# Get high-severity alerts
python3 siem-client.py --command high-severity --hours 1

# Get anomalies
python3 siem-client.py --command anomalies --hours 24
```

### Using curl

```bash
# Get alerts
curl -u elastic:change_me_elastic_password http://localhost:9200/siem-alerts-*/_search?pretty

# Get threats
curl -u elastic:change_me_elastic_password http://localhost:9200/siem-threats-*/_search?pretty

# Get anomalies
curl -u elastic:change_me_elastic_password http://localhost:9200/siem-anomalies-*/_search?pretty

# Count alerts
curl -u elastic:change_me_elastic_password http://localhost:9200/siem-alerts-*/_count?pretty
```

## Performance Testing

### Load Testing

Generate high-volume events to test performance:

```bash
# Generate 1000 normal events
python3 -c "
import socket, json, time
for i in range(1000):
    event = {
        'event_type': 'connection_attempt',
        'src_ip': f'192.168.1.{i % 254}',
        'dst_ip': f'10.0.0.{i % 100}',
        'src_port': 10000 + i,
        'dst_port': 443,
        'packet_count': 1,
        'byte_count': 100
    }
    sock = socket.socket()
    sock.connect(('localhost', 5000))
    sock.sendall((json.dumps(event) + '\n').encode())
    sock.close()
    if i % 100 == 0:
        print(f'Sent {i} events')
"

# Monitor resource usage
docker stats

# Check indexing speed
curl -u elastic:change_me_elastic_password http://localhost:9200/siem-logs-*/_count
```

### Latency Testing

Measure end-to-end latency:

```bash
# Send event and measure time to index
time echo '{"event_type":"test","src_ip":"1.1.1.1","dst_ip":"2.2.2.2","src_port":80,"dst_port":443}' | nc localhost 5000

# Query Elasticsearch for that event
curl -u elastic:change_me_elastic_password http://localhost:9200/siem-logs-*/_search \
  -H 'Content-Type: application/json' \
  -d '{"query": {"match": {"src_ip": "1.1.1.1"}}}'
```

## Troubleshooting Tests

### Issue: No events appearing in Kibana

**Checklist**:
```bash
# 1. Check Logstash is running
docker-compose ps | grep logstash

# 2. Check Elasticsearch has indices
curl -u elastic:change_me_elastic_password http://localhost:9200/_cat/indices

# 3. Check Logstash logs
docker-compose logs logstash | grep -i error

# 4. Try sending test event
echo '{"test":"data"}' | nc localhost 5000

# 5. Check ES can be reached from Logstash
docker-compose exec logstash curl http://elasticsearch:9200
```

### Issue: Detection engines not creating alerts

**Checklist**:
```bash
# 1. Check detection engine is running
docker-compose ps | grep detector

# 2. View detection logs
docker-compose logs anomaly-detector | tail -20
docker-compose logs threat-detector | tail -20

# 3. Check Redis connection
docker-compose exec redis redis-cli ping

# 4. Verify queues exist
docker-compose exec redis redis-cli KEYS "*.queue"

# 5. Check alerting engine is running
docker-compose logs alerting-engine | tail -20
```

### Issue: High CPU/Memory usage

**Solutions**:
```bash
# Reduce batch size in Logstash
# Edit logstash/config/logstash.yml:
# pipeline.batch.size: 50  (reduced from 125)

# Reduce Elasticsearch heap
# Edit docker-compose.yml:
# ES_JAVA_OPTS: -Xms256m -Xmx256m  (reduced from 512m)

# Restart services
docker-compose restart
```

## Test Report Template

```
===========================================
AI-SIEM Test Report
===========================================

Date: [DATE]
Tester: [NAME]
Test Environment: [DESCRIPTION]

Test Cases Run:
☐ Test 1: Normal Traffic
  Status: [ ] PASS [ ] FAIL
  Notes: 

☐ Test 2: Brute Force Detection
  Status: [ ] PASS [ ] FAIL
  Expected: 8 failed logins
  Actual: [COUNT]
  Notes:

☐ Test 3: Port Scan Detection
  Status: [ ] PASS [ ] FAIL
  Expected: Port scan alert
  Actual: [YES/NO]
  Notes:

☐ Test 4: DDoS Detection
  Status: [ ] PASS [ ] FAIL
  Expected: CRITICAL alert
  Actual: [YES/NO]
  Notes:

☐ Test 5: Data Exfiltration
  Status: [ ] PASS [ ] FAIL
  Expected: Large transfer detected
  Actual: [YES/NO]
  Notes:

☐ Test 6: Anomaly Detection
  Status: [ ] PASS [ ] FAIL
  Expected: Anomalies scored
  Actual: [COUNT]
  Notes:

☐ Test 7: Kibana Dashboard
  Status: [ ] PASS [ ] FAIL
  Notes:

☐ Test 8: Grafana Dashboard
  Status: [ ] PASS [ ] FAIL
  Notes:

☐ Test 9: Alert Generation
  Status: [ ] PASS [ ] FAIL
  Expected: Multiple alerts
  Actual: [COUNT]
  Notes:

Overall Result: [ ] PASS [ ] FAIL

Issues Found:
- [Issue 1]
- [Issue 2]

Performance Metrics:
- Events ingested: [COUNT]
- Average latency: [TIME]
- Alerts generated: [COUNT]
- Memory used: [MB]
- CPU usage: [%]

Recommendations:
- [Recommendation 1]
- [Recommendation 2]

Signed: ________________________  Date: __________
```

## Continuous Testing

### Daily Health Check

```bash
#!/bin/bash
# Run daily to verify system health

python3 siem-client.py --command stats
python3 siem-client.py --command high-severity --hours 24

# Check service status
docker-compose ps

# Generate sample events
python3 sample-data/generate_logs.py --scenario normal --count 20

# Verify detection worked
sleep 60
python3 siem-client.py --command anomalies --hours 1
```

---

**Next Steps**: Run the full scenario test and verify all detections work as expected!
