# Automated Attack Response System - Implementation Summary

## ✅ What Was Created

### 1. Automated Response Service (`automated-response/`)

**Files created:**
- `main.py` - Core blocking logic (18KB, ~600 lines)
- `Dockerfile` - Container with iptables support
- `requirements.txt` - Python dependencies
- `README.md` - Comprehensive documentation

**Key Features:**
- ✅ Automatic IP blocking for critical/high severity threats
- ✅ Port blocking for specific attack types (port scan, DDoS)
- ✅ Auto-expiration system (blocks expire automatically)
- ✅ iptables integration with custom SIEM_BLOCK chain
- ✅ Dry-run mode for testing
- ✅ Full logging to Elasticsearch
- ✅ Redis pub/sub integration
- ✅ Persistent block tracking in Redis

### 2. Docker Integration

**Updated `docker-compose.yml`:**
```yaml
automated-response:
  - NET_ADMIN capability for iptables
  - Environment configuration (auto-block, duration, dry-run)
  - Redis and Elasticsearch integration
  - Auto-restart on failure
```

### 3. Alerting Integration

**Updated `alerting/main.py`:**
- Now publishes to 'alerts' channel for automated response
- Maintains backward compatibility with 'siem:alerts'

### 4. Documentation

**Created:**
- `automated-response/README.md` - Service documentation
- `TESTING_AUTO_RESPONSE.md` - Testing guide
- `test_blocking.py` - Test script to simulate attacks
- Updated main `README.md` with automated response section

## 🔧 How It Works

### Flow Diagram

```
┌─────────────────┐
│  Malicious IP   │
│  Sends Events   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Logstash      │ ← Event ingestion
│   Port 5000     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Elasticsearch   │ ← Storage
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Threat Detector │ ← Pattern detection
│  (runs every    │   - Brute force (5+ in 10 min)
│   30 seconds)   │   - Port scan (20+ ports)
└────────┬────────┘   - DDoS (1000+ req/min)
         │
         ▼
┌─────────────────┐
│  Redis Queue    │ ← Threat storage
│ threats:queue   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Alerting Engine │ ← Alert creation
│  - Evaluates    │
│  - Deduplicates │
│  - Publishes    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Redis Pub/Sub  │ ← Real-time messaging
│ 'alerts' channel│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  Automated Response System  │ ← THIS IS NEW!
│                             │
│  1. Receives alert          │
│  2. Checks severity         │
│  3. Executes iptables:      │
│     - Block IP (DROP)       │
│     - Block port (DROP)     │
│  4. Tracks expiration       │
│  5. Auto-unblocks later     │
└─────────────────────────────┘
         │
         ▼
    ┌─────────┐
    │ BLOCKED │ ← Attack stopped!
    └─────────┘
```

## 🎯 Blocking Rules Implemented

| Threat Type | Action | Duration | Trigger |
|-------------|--------|----------|---------|
| **Critical Severity** | Block source IP | 120 min | Any critical threat |
| **High Severity** | Block source IP | 60 min | Any high threat |
| **Port Scan** | Block target port | 30 min | 20+ ports in 5 min |
| **DDoS Attack** | Block IP + port | 120/30 min | 1000+ req in 1 min |
| **Brute Force** | Block source IP | 60 min | 5+ failed logins |

## 🔐 Security Implementation

### iptables Structure

```bash
# Custom chain created
iptables -N SIEM_BLOCK

# Inserted into INPUT chain
iptables -I INPUT -j SIEM_BLOCK

# Example rules added dynamically
iptables -I SIEM_BLOCK -s 192.168.100.99 -j DROP       # Block IP
iptables -I SIEM_BLOCK -p tcp --dport 8080 -j DROP     # Block port
```

### Verification Commands

```bash
# Check firewall rules
docker exec ai-siem-response iptables -L SIEM_BLOCK -n -v

# View blocked IPs
docker exec ai-siem-response python -c "
from main import AutomatedResponseSystem
import json
system = AutomatedResponseSystem()
print(json.dumps(system.get_status(), indent=2))
"

# Monitor real-time logs
docker logs ai-siem-response -f
```

## 📊 Logging & Auditing

All actions are logged to Elasticsearch index: `siem-response-actions-YYYY.MM.DD`

**Logged Information:**
- Action type (block_ip, unblock_ip, block_port, unblock_port)
- Target (IP address or port)
- Reason (threat type, severity)
- Timestamp
- Duration
- Associated alert_id
- Dry-run status

**Query Example:**
```bash
curl "localhost:9200/siem-response-actions-*/_search?pretty"
```

## ⚙️ Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_BLOCK_ENABLED` | true | Enable/disable blocking |
| `BLOCK_DURATION_MINUTES` | 60 | Default block duration |
| `DRY_RUN_MODE` | false | If true, only logs (no actual blocking) |

### Modes of Operation

1. **Active Mode** (DRY_RUN_MODE=false)
   - Actually executes iptables commands
   - Blocks real traffic
   - Requires NET_ADMIN capability
   - **Current mode: ACTIVE**

2. **Dry-Run Mode** (DRY_RUN_MODE=true)
   - Only logs what would be blocked
   - Safe for testing
   - No actual firewall changes

## 🧪 Testing

### Test Script Created: `test_blocking.py`

Simulates:
1. Brute force attack (10 failed logins)
2. Port scanning (25 different ports)
3. DDoS attack (100 rapid requests)

**Run it:**
```bash
python3 test_blocking.py
```

### Manual Testing

```bash
# Send high-severity event
echo '{"event_type":"authentication_failed","src_ip":"192.168.100.99","dst_ip":"10.0.0.1","username":"admin","severity":"high"}' | nc localhost 5000

# Wait 30-60 seconds, then check
docker logs ai-siem-response --tail 20
```

## 📈 Current Status

✅ **Service Running**: `ai-siem-response` container up
✅ **Mode**: ACTIVE (blocking enabled)
✅ **Auto-block**: ENABLED
✅ **Duration**: 60 minutes default
✅ **iptables Chain**: SIEM_BLOCK created
✅ **Monitoring**: Subscribed to 'alerts' channel
✅ **Integration**: Connected to Elasticsearch & Redis

**Verify:**
```bash
docker-compose ps | grep response
# Should show: ai-siem-response ... running
```

## 🔄 Integration Points

### With Threat Detection
- Receives threats via Redis alerts channel
- Responds to patterns: brute_force, port_scan, ddos_attack, privilege_escalation

### With Alerting Engine
- Subscribes to 'alerts' pub/sub channel
- Processes all critical/high severity alerts
- Takes immediate action based on severity

### With Elasticsearch
- Logs all blocking actions
- Creates indices: siem-response-actions-*
- Searchable audit trail

### With Redis
- Subscribes to 'alerts' channel (pub/sub)
- Stores block info with TTL
- Enables distributed tracking

## 🚀 What You Can Do Now

### 1. Test the System
```bash
python3 test_blocking.py
```

### 2. Monitor Activity
```bash
# Watch for blocks
docker logs ai-siem-response -f

# Check current blocks
docker exec ai-siem-response iptables -L SIEM_BLOCK -n
```

### 3. Simulate Attack
```bash
# Send multiple failed login attempts
for i in {1..8}; do
  echo '{"event_type":"authentication_failed","src_ip":"203.0.113.100","dst_ip":"10.0.0.1","username":"admin","severity":"high"}' | nc localhost 5000
  sleep 1
done
```

### 4. View Block Actions
```bash
# Query Elasticsearch
curl "localhost:9200/siem-response-actions-*/_search?pretty"
```

### 5. Check System Status
```bash
docker logs ai-siem-response | head -20
```

## ⚠️ Important Notes

### Security Considerations
- System is in **ACTIVE** mode - will actually block IPs
- Ensure you have console/physical access to the system
- Test thoroughly before production use
- Consider implementing IP whitelist for critical services
- Monitor false positives

### Network Requirements
- Container needs NET_ADMIN capability (already configured)
- For host-level blocking, uncomment `network_mode: host` in docker-compose.yml
- Currently blocks within container network namespace

### Limitations
- Blocks are not persistent across container restarts (by design)
- iptables rules apply at container level unless host network mode used
- No IP whitelist implemented yet (enhancement opportunity)

## 🎓 Next Enhancements (Optional)

Potential improvements you could add:

1. **Whitelist Management**
   - Prevent blocking of trusted IPs
   - Admin interface for whitelist

2. **Notification System**
   - Email alerts when IPs are blocked
   - Slack/Discord webhooks

3. **Geographic Blocking**
   - Block entire countries/regions
   - Integration with GeoIP databases

4. **Rate Limiting**
   - Throttle instead of full block
   - Graduated response system

5. **Web Dashboard**
   - View blocked IPs in real-time
   - Manual block/unblock interface
   - Block history and statistics

6. **Machine Learning Enhancement**
   - Learn legitimate traffic patterns
   - Auto-whitelist based on behavior
   - Reduce false positives

## 📚 Documentation Files

All documentation available:
- `README.md` - Main project README (updated)
- `automated-response/README.md` - Detailed service documentation
- `TESTING_AUTO_RESPONSE.md` - Testing guide
- `ARCHITECTURE.md` - System architecture (if you want to update it)

## ✨ Summary

You now have a **fully functional automated attack response system** that:

1. ✅ Monitors for security threats in real-time
2. ✅ Automatically blocks malicious IPs and ports
3. ✅ Uses industry-standard iptables firewall
4. ✅ Logs all actions for audit trail
5. ✅ Auto-expires blocks (no manual cleanup needed)
6. ✅ Integrates seamlessly with existing SIEM
7. ✅ Provides dry-run mode for testing
8. ✅ Is fully documented and ready to use

**The system is running right now** and will automatically block any critical or high-severity threats detected by your AI-SIEM!
