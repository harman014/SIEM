# AI-SIEM Architecture & Design Documentation

## System Overview

AI-SIEM is a containerized, open-source Security Information and Event Management platform designed for SMBs. It combines centralized log management, real-time threat detection, and machine learning-based anomaly detection.

## Architecture Layers

### 1. Data Ingestion Layer

**Purpose**: Collect security events from diverse sources

**Components**:
- **Logstash**: Central log processing pipeline
  - TCP/UDP listeners for network events
  - File-based input for application logs
  - JSON/Syslog parsing and enrichment
  - GeoIP enrichment for IPs
  - Time-based filtering and transformation

**Data Sources**:
- Web servers (Apache, Nginx)
- Firewalls (pfSense, iptables)
- OS logs (syslog, auth.log)
- Applications (custom JSON APIs)
- Endpoint agents (Filebeat, Auditbeat)

**Processing Pipeline**:
```
Raw Log → Logstash Intake → Parsing → Enrichment → Elasticsearch Index
```

**Key Metrics**:
- Throughput: 100k+ events/day per instance
- Latency: <1 second end-to-end
- Reliability: Persisted queue prevents data loss

---

### 2. Data Storage & Search Layer

**Purpose**: Store, index, and search security events efficiently

**Components**:
- **Elasticsearch**: Distributed search and analytics engine
  - Full-text search capability
  - Time-series data optimization
  - Real-time indexing
  - Aggregation framework for analytics

**Index Strategy**:
```
siem-logs-YYYY.MM.DD      → Raw security events (24h rolling)
siem-threats-YYYY.MM.DD   → Detected threat incidents
siem-anomalies-YYYY.MM.DD → Anomaly detection results
siem-alerts-YYYY.MM.DD    → Generated alerts
```

**Retention Policy**:
- Hot (recent data): 7 days - full search capability
- Warm: 8-30 days - searchable but slower
- Cold: 31-90 days - archived (optional)

**Scaling**:
- Single-node: <1M events/day
- 3-node cluster: 1M-10M events/day
- 5+ node cluster: 10M+ events/day

---

### 3. Detection & Analysis Layer

#### 3A. Threat Detection Engine

**Algorithm**: Pattern matching and rule-based detection

**Detection Patterns**:

| Threat | Signal | Threshold | Action |
|--------|--------|-----------|--------|
| **Brute Force** | auth_failed | 5 in 10min | Alert |
| **Port Scan** | connection_attempt | 20 ports in 5min | Alert |
| **DDoS** | http_request | 1000 req/min | Escalate |
| **Privilege Esc.** | elevation | 3 attempts | Escalate |
| **Data Exfil** | data_transfer | >100MB/5min | Alert |

**Query Strategy**:
```python
def detect_brute_force():
    # Aggregate failed authentications by source IP
    # Last 10 minutes
    # Min 5 attempts threshold
    # Return matching IPs
```

**Performance**:
- Query interval: 30 seconds
- Search scope: Last 10 minutes
- Results: Near real-time

#### 3B. Anomaly Detection Engine

**Algorithm**: Isolation Forest (scikit-learn)

**How It Works**:
1. **Training Phase**: Learns normal behavior from historical data
   - 24 hours of baseline data
   - Extracts 5 numerical features per event
   - Trains on ~10,000 samples

2. **Detection Phase**: Identifies statistical outliers
   - Scores each incoming event
   - Flags scores below anomaly threshold (-0.5)
   - Updates with new data every minute

3. **Retraining**: Maintains accuracy over time
   - Retrains every 6 hours
   - Uses newest 24 hours of data
   - Adapts to evolving baselines

**Extracted Features**:
```python
features = [
    src_port,           # Source port
    dst_port,           # Destination port  
    packet_count,       # Number of packets
    byte_count,         # Total bytes transferred
    bytes_per_packet    # Derived feature
]
```

**Advantages**:
- Unsupervised learning (no labeled training data needed)
- Efficient (linear time complexity)
- Works with mixed normal/attack data
- Adapts to concept drift

---

### 4. Real-Time Processing Layer

**Purpose**: Queue and process detected threats for immediate response

**Components**:
- **Redis**: In-memory data structure store
  - Message queues for threat/anomaly results
  - Pub/Sub for real-time notifications
  - Session cache for alert deduplication
  - Configuration cache

**Message Flow**:
```
Threat Detector → threats:queue (Redis)
                       ↓
                Alerting Engine (consumer)
                       ↓
         Rule evaluation & deduplication
                       ↓
                siem:alerts channel (pub/sub)
                       ↓
          Elasticsearch + Redis notification
```

**Queue Structure**:
- `threats:queue` - Array of threat objects
- `anomalies:queue` - Array of anomaly objects  
- `alerts:queue` - Processed alerts ready for action
- `siem:alerts` - Pub/Sub channel for live alerts

---

### 5. Visualization & Analysis Layer

#### 5A. Kibana (ELK Stack Native)

**Purpose**: Raw log exploration and analysis

**Features**:
- Search and filter raw events
- Time-series analysis
- Histogram and timeline views
- Field analysis
- Discover interface for ad-hoc queries

**Use Cases**:
- Detailed log investigation
- Incident forensics
- Custom ad-hoc queries
- Field-level analytics

#### 5B. Grafana (Advanced Dashboards)

**Purpose**: High-level security metrics and KPIs

**Dashboard Types**:

1. **Security Threat Overview**
   - Event timeline
   - High-severity event count gauge
   - Event distribution by type
   - Severity level breakdown

2. **Network Anomalies** (custom)
   - Unusual traffic patterns
   - Anomaly score trends
   - Top anomalous sources
   - Protocol distribution

3. **Attack Detection** (custom)
   - Brute force attempts
   - Port scan detections
   - DDoS patterns
   - Privilege escalation attempts

**Alerting**:
- Condition-based alerts
- Notification channels (email, webhook, Slack)
- Escalation policies

---

### 6. Alerting & Response Layer

**Purpose**: Generate actionable alerts and enable incident response

**Components**:
- **Alerting Engine**: Python-based alert processor
  - Consumes threat/anomaly queue
  - Evaluates alert rules
  - Deduplicates similar alerts
  - Routes to appropriate channels

**Alert Workflow**:
```
Detection (Threat/Anomaly)
        ↓
    Redis Queue
        ↓
  Alerting Engine
        ↓
  Rule Evaluation (severity, type, source)
        ↓
  Deduplication Check (prevent spam)
        ↓
  Elasticsearch Index + Pub/Sub Publish
        ↓
  Notification Channels
    (Email, Slack, Webhook, SIEM)
```

**Alert Deduplication**:
- Cache key: `threat_type:source_ip:timestamp`
- TTL: 300 seconds (configurable)
- Prevents alert fatigue
- Groups similar incidents

---

## Data Flow Examples

### Example 1: Brute Force Detection

```
Time  Event                               Component
────  ─────                               ─────────
T0    SSH failure from 192.168.1.50      → Logstash (ingest)
T1    Parsed, enriched                   → Elasticsearch (index)
T2    Index created: siem-logs-YYYY.MM.DD
T3    Threat detector queries ES         → Get 5+ failures from IP
T4    Match found: 7 attempts in 10min   → Create threat object
T5    Published to Redis                 → threats:queue
T6    Alerting engine consumes           → Evaluate rules
T7    Rule: auth_failed > 5 = HIGH       → Match!
T8    Check dedup cache                  → No recent alert
T9    Create alert, store ES             → siem-alerts-*
T10   Publish to siem:alerts channel     → Live notification
T11   Grafana dashboard updates          → Show alert
```

### Example 2: Anomaly Detection

```
Time  Event                                Component
────  ─────                                ─────────
T0    Unusual packet rate detected        → Normal traffic event
T1    Logstash ingests                    → Parsed & indexed
T2    Anomaly detector fetches last hour  → siem-logs-*
T3    Extracts features [src_port, ...]   → Numerical vectors
T4    Scores with IF model                → Score: -0.75
T5    Below threshold (-0.5)              → Flag as anomaly
T6    Create anomaly object               → Store in Redis
T7    Alerting engine processes           → anomalies:queue
T8    Check severity from score           → high severity (-0.75)
T9    Rule: anomaly_score < -0.5 = HIGH   → Match!
T10   Deduplication: No recent same      → Proceed
T11   Index alert ES                      → siem-anomalies-*
T12   Publish live alert                  → siem:alerts
```

---

## Scalability Considerations

### Horizontal Scaling

**Elasticsearch Cluster**:
```yaml
# Single Node (SMB small)
node.roles: [master, data]
ES_JAVA_OPTS: -Xms512m -Xmx512m

# 3-Node Cluster (SMB medium)
node-1: -Xms1g -Xmx1g (master)
node-2: -Xms1g -Xmx1g (data)
node-3: -Xms1g -Xmx1g (data)

# 5+ Node Cluster (Enterprise)
3× master nodes
3× data nodes (-Xms2g -Xmx2g)
1+ ingest nodes
```

**Logstash Pipeline**:
- Single instance: 100k events/day
- Add workers: `pipeline.workers: 4` (default: 1)
- Pipeline batch: Tune `pipeline.batch.size`

**Detection Engines**:
- Stateless design enables horizontal scaling
- Load balance queries across nodes
- Reduce search interval during high load

### Vertical Scaling

**Memory Configuration**:
```
Events/day → Elasticsearch Heap → Logstash Heap → Anomaly Worker
─────────────────────────────────────────────────────────────────
<100k      → 512MB              → 256MB           → 512MB
100k-1M    → 1GB                → 512MB           → 1GB
1M-10M     → 2GB                → 1GB             → 2GB
10M+       → 4GB+               → 2GB+            → 4GB+
```

---

## Security Architecture

### Authentication & Authorization

**Current**:
- Basic auth (username/password)
- Elasticsearch native realm
- Kibana RBAC
- Redis ACL (Redis 6+)

**Future**:
- OAuth2/OIDC integration
- LDAP/Active Directory
- Fine-grained RBAC
- API key-based access

### Network Security

**Isolation**:
- Docker network (siem-network)
- Internal communication only
- No services exposed to internet

**Hardening**:
- Disable unnecessary X-Pack features
- Enable transport security
- Use secrets management
- Regular security updates

### Data Protection

**Encryption**:
- TLS for inter-service communication
- At-rest encryption (optional)
- Password hashing (bcrypt for custom systems)

**Retention**:
- Configurable data retention (30-90 days)
- Automatic purge of old indices
- Compliance with data retention policies

---

## Performance Optimization

### Query Optimization

**Elasticsearch**:
```
- Use filter context (cached) vs query context
- Limit fields in _source
- Use aggregations instead of terms buckets
- Implement index sharding strategy
```

**Search Scope**:
```
- Brute force: Last 10 minutes
- Port scan: Last 5 minutes
- DDoS: Last 1 minute
- Anomaly check: Last 1 hour
```

### Caching Strategy

**Redis Cache**:
- Alert dedup: 300 second TTL
- Configuration: Persistent
- Feature cache: Sliding window (6 hours)

**Query Caching**:
- Elasticsearch query cache
- Logstash filter cache
- Grafana dashboard cache

### Batch Processing

**Logstash**:
```
pipeline.batch.size: 125
pipeline.batch.delay: 50ms
→ Optimal throughput/latency balance
```

---

## Monitoring & Observability

### Key Metrics to Track

**System**:
- Elasticsearch cluster health
- Logstash queue depth
- Redis memory usage
- Container resource usage

**Data**:
- Events per second ingestion rate
- Index size growth rate
- Query latency percentiles
- Detection accuracy (TP/FP rate)

**Application**:
- Alert generation rate
- Alert dedup effectiveness
- Model retraining frequency
- Pipeline error rate

---

## Future Enhancements

### Short-term (v1.1)
- [ ] Email notification integration
- [ ] Slack/Teams webhook support
- [ ] Additional Grafana dashboards
- [ ] Case management system

### Medium-term (v1.2)
- [ ] Advanced ML models (LSTM, Autoencoders)
- [ ] Threat intelligence feed integration
- [ ] API for external integrations
- [ ] SOAR integration (automation)

### Long-term (v2.0)
- [ ] Distributed detection (multiple locations)
- [ ] Graph database for relationships
- [ ] Custom plugin architecture
- [ ] Cloud-native Kubernetes deployment

---

**Last Updated**: December 2025
**Version**: 1.0 Architecture
