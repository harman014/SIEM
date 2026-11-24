# 🛡️ Automated Attack Response System

## ✅ SYSTEM ACTIVE

Your AI-SIEM now has **automated attack blocking** capabilities!

---

## 🎯 What It Does

When a **high or critical severity threat** is detected, the system **automatically blocks** the attacker:

```
🔴 Attack Detected → 🚨 Alert Created → ⚡ IP/Port BLOCKED
```

### Blocking Rules

| Severity | Action | Duration |
|----------|--------|----------|
| 🔴 **Critical** | Block source IP | **120 minutes** |
| 🟠 **High** | Block source IP | **60 minutes** |
| 🟡 Medium | Log only | - |
| 🟢 Low | Log only | - |

### Attack Types Blocked

- ✅ **Brute Force** (5+ failed logins) → Block IP
- ✅ **Port Scanning** (20+ ports) → Block IP + Port
- ✅ **DDoS Attack** (1000+ requests) → Block IP
- ✅ **Privilege Escalation** → Block IP

---

## 🧪 Test It Now!

### Option 1: Run Test Suite

```bash
python3 test_blocking.py
```

This simulates:
- Brute force attacks
- Port scanning
- DDoS attacks

### Option 2: Quick Manual Test

```bash
# Send a high-severity threat
echo '{"event_type":"authentication_failed","src_ip":"192.168.100.99","dst_ip":"10.0.0.1","username":"admin","severity":"high"}' | nc localhost 5000

# Wait 30 seconds, then check
docker logs ai-siem-response --tail 20
```

---

## 📊 Monitor Blocking Activity

### Check Current Blocks

```bash
# View blocked IPs
docker exec ai-siem-response python -c "
from main import AutomatedResponseSystem
import json
system = AutomatedResponseSystem()
print(json.dumps(system.get_status(), indent=2))
"
```

### View Firewall Rules

```bash
# See iptables blocks
docker exec ai-siem-response iptables -L SIEM_BLOCK -n -v
```

### Watch Live Logs

```bash
# Real-time monitoring
docker logs ai-siem-response -f
```

### Query Elasticsearch

```bash
# See all blocking actions
curl "localhost:9200/siem-response-actions-*/_search?pretty"
```

---

## 🔧 Configuration

Current settings (in `docker-compose.yml`):

```yaml
automated-response:
  environment:
    - AUTO_BLOCK_ENABLED=true     # ✅ Blocking enabled
    - BLOCK_DURATION_MINUTES=60   # Default: 1 hour
    - DRY_RUN_MODE=false          # ✅ ACTIVE mode
```

### Switch to Test Mode (No Real Blocking)

```yaml
- DRY_RUN_MODE=true  # Will only log, not block
```

Then restart:
```bash
docker-compose restart automated-response
```

---

## 🎬 How It Works

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│  1. Attacker sends malicious events                │
│     ↓                                               │
│  2. Logstash receives (port 5000)                  │
│     ↓                                               │
│  3. Elasticsearch stores events                    │
│     ↓                                               │
│  4. Threat Detector analyzes patterns              │
│     ↓                                               │
│  5. Alert created if threshold exceeded            │
│     ↓                                               │
│  6. Automated Response System receives alert       │
│     ↓                                               │
│  7. ⚡ iptables BLOCKS attacker IP                  │
│     ↓                                               │
│  8. Block logged to Elasticsearch                  │
│     ↓                                               │
│  9. After 60 minutes: AUTO-UNBLOCK                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Example

```bash
# Attacker: 192.168.100.50
# Action: 10 failed login attempts

→ Threat detected: Brute Force
→ Severity: HIGH
→ Response: iptables -I SIEM_BLOCK -s 192.168.100.50 -j DROP
→ Result: All traffic from 192.168.100.50 BLOCKED for 60 minutes
```

---

## 📋 Current Status

Run this to check status:

```bash
docker-compose ps | grep response
docker logs ai-siem-response --tail 10
```

Expected output:
```
ai-siem-response   "python -u main.py"   running

INFO - Auto-block: ENABLED
INFO - Mode: ACTIVE (blocking enabled)
INFO - Subscribed to 'alerts' channel, waiting for alerts...
```

---

## 🔐 Security Notes

⚠️ **Important:**

1. **Testing First**: Test in dry-run mode before production
2. **Console Access**: Ensure you have physical/console access to the host
3. **Whitelist**: Consider implementing IP whitelist for critical services
4. **Monitoring**: Regularly check for false positives
5. **Backup Access**: Have alternative access methods

---

## 📚 Documentation

- **Detailed docs**: [`automated-response/README.md`](automated-response/README.md)
- **Testing guide**: [`TESTING_AUTO_RESPONSE.md`](TESTING_AUTO_RESPONSE.md)
- **Implementation**: [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md)
- **Main README**: [`README.md`](README.md)

---

## 🎯 Quick Commands

```bash
# View all services
docker-compose ps

# Check blocking logs
docker logs ai-siem-response -f

# Check threat detection
docker logs ai-siem-threat-detector -f

# Check alerting
docker logs ai-siem-alerting -f

# View current blocks
docker exec ai-siem-response iptables -L SIEM_BLOCK -n

# Manually unblock an IP
docker exec ai-siem-response python -c "
from main import AutomatedResponseSystem
system = AutomatedResponseSystem()
system.unblock_ip('192.168.100.99')
"

# Get status
docker exec ai-siem-response python -c "
from main import AutomatedResponseSystem
import json
system = AutomatedResponseSystem()
print(json.dumps(system.get_status(), indent=2))
"
```

---

## 🚀 Ready to Use!

Your AI-SIEM now has **automatic attack blocking** enabled and running!

**Try it:**
1. Run `python3 test_blocking.py`
2. Watch the logs: `docker logs ai-siem-response -f`
3. See the blocks happen in real-time!

---

**System Status**: 🟢 **ACTIVE & MONITORING**

All services running. Automated response system is listening for threats and ready to block attacks automatically.
