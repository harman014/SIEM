# Automated Response System

## Overview
The Automated Response System automatically blocks malicious IPs and ports based on security threats detected by the AI-SIEM system.

## Features

### Automatic IP Blocking
- Blocks source IPs for **critical** and **high** severity threats
- Critical threats: blocked for 2x the default duration (120 minutes by default)
- High threats: blocked for default duration (60 minutes by default)

### Automatic Port Blocking
- Blocks destination ports for specific attack types:
  - Port scanning attacks
  - DDoS attacks
- Default port block duration: 30 minutes

### Auto-Expiration
- Blocks automatically expire after the configured duration
- System checks for expired blocks every 60 seconds
- Automatic cleanup and unblocking

### Logging & Auditing
- All blocking actions logged to Elasticsearch
- Index: `siem-response-actions-YYYY.MM.DD`
- Tracks: block/unblock events, reasons, timestamps, durations

## Configuration

Environment variables in `docker-compose.yml`:

```yaml
- AUTO_BLOCK_ENABLED=true          # Enable/disable automatic blocking
- BLOCK_DURATION_MINUTES=60        # Default block duration
- DRY_RUN_MODE=false               # true = log only, false = actually block
```

## Modes

### Active Mode (DRY_RUN_MODE=false)
- Actually executes iptables commands
- Blocks traffic at the firewall level
- Requires NET_ADMIN capability

### Dry Run Mode (DRY_RUN_MODE=true)
- Only logs what would be blocked
- Safe for testing
- No actual firewall changes

## How It Works

1. **Alert Detection**: Subscribes to Redis 'alerts' channel
2. **Threat Analysis**: Evaluates alert severity and type
3. **Action Decision**: Determines if blocking is warranted
4. **Execution**: Applies iptables rules to block traffic
5. **Tracking**: Stores block info in Redis and Elasticsearch
6. **Auto-Unblock**: Removes blocks after expiration

## Blocking Rules

| Alert Severity | Source IP | Duration      |
|----------------|-----------|---------------|
| Critical       | ✓ Block   | 120 minutes   |
| High           | ✓ Block   | 60 minutes    |
| Medium         | No action | -             |
| Low            | No action | -             |

| Attack Type    | Port Block | Duration    |
|----------------|------------|-------------|
| Port Scan      | ✓ Block    | 30 minutes  |
| DDoS Attack    | ✓ Block    | 30 minutes  |

## iptables Implementation

The system creates a custom iptables chain called `SIEM_BLOCK`:

```bash
# Chain structure
iptables -N SIEM_BLOCK
iptables -I INPUT -j SIEM_BLOCK

# IP block example
iptables -I SIEM_BLOCK -s 192.168.1.100 -j DROP

# Port block example
iptables -I SIEM_BLOCK -p tcp --dport 8080 -j DROP
```

## Monitoring

### Check Blocked IPs/Ports
```bash
docker exec ai-siem-response iptables -L SIEM_BLOCK -n
```

### View Logs
```bash
docker logs ai-siem-response
```

### Query Response Actions in Elasticsearch
```json
GET /siem-response-actions-*/_search
{
  "query": {
    "match_all": {}
  },
  "sort": [
    { "@timestamp": "desc" }
  ]
}
```

## Testing

### Test with Dry Run Mode
1. Set `DRY_RUN_MODE=true` in docker-compose.yml
2. Restart service: `docker-compose restart automated-response`
3. Generate test alerts
4. Check logs to see what would be blocked

### Generate Test Alert
```bash
# Send high-severity threat
echo '{"event_type":"brute_force","src_ip":"192.168.1.100","severity":"high"}' | nc localhost 5000
```

## Security Considerations

⚠️ **Important**:
- Only run in Active Mode on properly secured systems
- Test thoroughly in Dry Run Mode first
- Be careful not to block legitimate traffic
- Ensure you have console access in case of misconfiguration
- Monitor blocked IPs regularly

## Troubleshooting

### Issue: Blocks not being applied
**Solution**: Check container has NET_ADMIN capability:
```bash
docker inspect ai-siem-response | grep CapAdd
```

### Issue: Permission denied errors
**Solution**: Ensure container is running with sufficient privileges

### Issue: Blocks persisting after restart
**Solution**: iptables rules are not persistent by default. Use iptables-persistent if needed.

## Manual Control

### Manually Block IP
```bash
docker exec ai-siem-response python -c "
from main import AutomatedResponseSystem
import os
os.environ['DRY_RUN_MODE'] = 'false'
system = AutomatedResponseSystem()
system.block_ip('192.168.1.100', 'Manual block', 'manual-001', 60)
"
```

### Manually Unblock IP
```bash
docker exec ai-siem-response python -c "
from main import AutomatedResponseSystem
system = AutomatedResponseSystem()
system.unblock_ip('192.168.1.100')
"
```

### Check Status
```bash
docker exec ai-siem-response python -c "
from main import AutomatedResponseSystem
import json
system = AutomatedResponseSystem()
print(json.dumps(system.get_status(), indent=2))
"
```

## Integration with Other Services

The Automated Response System integrates with:
- **Alerting Engine**: Receives alerts via Redis pub/sub
- **Elasticsearch**: Stores response action logs
- **Redis**: Alert communication and block persistence
- **Threat Detection**: Responds to detected threats
- **Anomaly Detection**: Responds to anomaly alerts

## Future Enhancements

- [ ] Geographic IP blocking
- [ ] Whitelist management
- [ ] Rate limiting instead of complete blocks
- [ ] Email notifications for blocks
- [ ] Web dashboard for block management
- [ ] Integration with external threat feeds
- [ ] Automatic whitelist learning
