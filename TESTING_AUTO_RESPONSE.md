# Testing the Automated Response System

## ✅ System Status

All services are running! The automated response system is now active and monitoring for threats.

```bash
# Check status
docker-compose ps

# View logs
docker logs ai-siem-response --tail 50
```

## 🧪 Test the Blocking Mechanism

### Method 1: Quick Test with Simulated Attack

Run the test script to simulate various attacks:

```bash
python3 test_blocking.py
```

This will simulate:
1. **Brute force attack** (10 failed login attempts)
2. **Port scanning** (25 port scans)
3. **DDoS attack** (100 rapid HTTP requests)

### Method 2: Manual Test Event

Send a high-severity threat event directly:

```bash
echo '{"event_type":"authentication_failed","src_ip":"192.168.100.99","dst_ip":"10.0.0.1","username":"admin","severity":"high","timestamp":'$(date +%s)'}' | nc localhost 5000
```

Wait 30-60 seconds for the threat detection and response:

```bash
# Watch for blocking action
docker logs ai-siem-response -f
```

## 📊 Verify Blocking Actions

### 1. Check Container Logs

```bash
# Automated response logs
docker logs ai-siem-response --tail 100

# Look for lines like:
# ✓ BLOCKED IP: 192.168.100.99 - Reason: HIGH threat: brute_force_login
```

### 2. View iptables Rules

```bash
# Check firewall rules created
docker exec ai-siem-response iptables -L SIEM_BLOCK -n -v
```

Output example:
```
Chain SIEM_BLOCK (1 references)
 pkts bytes target     prot opt in     out     source               destination
    0     0 DROP       all  --  *      *       192.168.100.99      0.0.0.0/0
```

### 3. Query Elasticsearch for Response Actions

```bash
# View all blocking actions
curl -X GET "localhost:9200/siem-response-actions-*/_search?pretty" \
     -H 'Content-Type: application/json' \
     -d '{
       "query": {"match_all": {}},
       "sort": [{"@timestamp": "desc"}],
       "size": 10
     }'
```

### 4. Monitor Redis Alerts Channel

```bash
# Subscribe to alerts channel in real-time
docker exec ai-siem-redis redis-cli -a change_me_redis_password SUBSCRIBE alerts
```

### 5. Check Threat Detection

```bash
# View threat detector logs
docker logs ai-siem-threat-detector --tail 100
```

### 6. Check Alerting Engine

```bash
# View alerting engine logs
docker logs ai-siem-alerting --tail 100
```

## 🎯 Expected Flow

When you send a malicious event:

```
1. Event arrives at Logstash (port 5000)
   ↓
2. Logstash processes and sends to Elasticsearch
   ↓
3. Threat Detection Engine queries Elasticsearch
   ↓
4. Detects pattern (e.g., 5+ failed logins)
   ↓
5. Creates threat object, pushes to Redis queue
   ↓
6. Alerting Engine processes threat
   ↓
7. Creates alert, publishes to Redis 'alerts' channel
   ↓
8. Automated Response System receives alert
   ↓
9. Evaluates severity (critical/high triggers block)
   ↓
10. Executes iptables command to block IP
    ↓
11. Logs action to Elasticsearch
    ↓
12. Stores block info in Redis for auto-expiration
```

## ⏱️ Timing

- **Threat detection cycle**: Every 10-30 seconds
- **Alert processing**: Near real-time (< 1 second)
- **Blocking execution**: Immediate (< 1 second)
- **Total time from event to block**: 30-60 seconds

## 🔧 Configuration Options

### Switch to Dry-Run Mode (Testing)

Edit `docker-compose.yml`:

```yaml
automated-response:
  environment:
    - DRY_RUN_MODE=true  # Change to true
```

Then restart:

```bash
docker-compose restart automated-response
```

In dry-run mode, it will **only log** what would be blocked, without actually blocking.

### Adjust Block Duration

```yaml
automated-response:
  environment:
    - BLOCK_DURATION_MINUTES=30  # Change to desired minutes
```

### Disable Auto-Blocking

```yaml
automated-response:
  environment:
    - AUTO_BLOCK_ENABLED=false  # Disable blocking
```

## 🛠️ Troubleshooting

### Issue: No blocking happens

**Check 1**: Verify AUTO_BLOCK_ENABLED=true
```bash
docker logs ai-siem-response | grep "Auto-block"
```

**Check 2**: Verify threat detection is running
```bash
docker logs ai-siem-threat-detector --tail 20
```

**Check 3**: Check if alerts are being generated
```bash
docker exec ai-siem-redis redis-cli -a change_me_redis_password LLEN alerts:queue
```

### Issue: Permission denied for iptables

The container needs NET_ADMIN capability (already configured in docker-compose.yml).

Verify:
```bash
docker inspect ai-siem-response | grep -A5 CapAdd
```

Should show:
```json
"CapAdd": [
    "NET_ADMIN",
    "NET_RAW"
],
```

### Issue: Want to manually unblock an IP

```bash
docker exec ai-siem-response python -c "
from main import AutomatedResponseSystem
system = AutomatedResponseSystem()
system.unblock_ip('192.168.100.99')
"
```

## 📈 Monitoring in Production

### Set up log aggregation
```bash
# Tail all relevant logs
docker-compose logs -f automated-response threat-detector alerting-engine
```

### Create Grafana dashboard
- Query `siem-response-actions-*` index
- Visualize blocked IPs over time
- Track block duration statistics
- Monitor auto-unblock events

### Set up alerts
- Configure email/Slack notifications when critical threats are blocked
- Alert on high blocking rate (possible false positives)

## 🎓 Example Attack Scenarios

### Scenario 1: Brute Force SSH Attack
```bash
# Simulate 8 failed SSH login attempts
for i in {1..8}; do
  echo "{\"event_type\":\"authentication_failed\",\"src_ip\":\"203.0.113.50\",\"dst_ip\":\"10.0.0.5\",\"service\":\"ssh\",\"port\":22,\"username\":\"root\",\"severity\":\"high\"}" | nc localhost 5000
  sleep 2
done
```

**Expected**: After 5 attempts, threat detected → alert created → IP `203.0.113.50` blocked

### Scenario 2: Port Scan Detection
```bash
# Use test_blocking.py for comprehensive port scan simulation
python3 test_blocking.py
# Select test #2
```

### Scenario 3: Check Current Blocks
```bash
# Get status programmatically
docker exec ai-siem-response python -c "
from main import AutomatedResponseSystem
import json
system = AutomatedResponseSystem()
print(json.dumps(system.get_status(), indent=2))
"
```

## 🚀 Next Steps

1. ✅ System is running and ready
2. Run `python3 test_blocking.py` to simulate attacks
3. Monitor logs: `docker logs ai-siem-response -f`
4. Check Kibana for threat visualizations: http://localhost:5601
5. View Grafana dashboards: http://localhost:3000
6. Query blocked IPs in Elasticsearch

---

**Security Note**: The automated response system is currently in ACTIVE mode. Make sure you:
- ✓ Test thoroughly in a non-production environment
- ✓ Have backup access to the system (not through the network)
- ✓ Monitor blocked IPs regularly to prevent false positives
- ✓ Configure proper whitelists for legitimate IPs
