"""
Threat Detection Engine for AI-SIEM
Correlates events with threat intelligence and detects known attack patterns
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List

import redis
from elasticsearch import Elasticsearch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
ES_HOST = os.getenv('ELASTICSEARCH_HOST', 'localhost')
ES_PORT = int(os.getenv('ELASTICSEARCH_PORT', 9200))
ES_USER = os.getenv('ELASTICSEARCH_USER', 'elastic')
ES_PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD', 'changeme')

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'changeme')


class ThreatDetectionEngine:
    """Detects known threats and attacks patterns"""

    def __init__(self):
        """Initialize ES and Redis connections"""
        try:
            self.es = Elasticsearch(
                [{'host': ES_HOST, 'port': ES_PORT, 'scheme': 'http'}],
                basic_auth=(ES_USER, ES_PASSWORD),
                request_timeout=30
            )
            logger.info("Connected to Elasticsearch")
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise

        try:
            self.redis = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                decode_responses=True
            )
            self.redis.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

        # Initialize threat signatures
        self.threat_signatures = self._load_threat_signatures()

    def _load_threat_signatures(self) -> Dict[str, Dict]:
        """Load known threat signatures"""
        return {
            'brute_force_login': {
                'name': 'Brute Force Login Attempt',
                'pattern': 'Failed authentication attempts',
                'threshold': 5,
                'timeframe_minutes': 10,
                'severity': 'high',
                'query_field': 'event_type',
                'query_value': 'authentication_failed'
            },
            'port_scan': {
                'name': 'Port Scanning Detected',
                'pattern': 'Multiple connection attempts to different ports',
                'threshold': 20,
                'timeframe_minutes': 5,
                'severity': 'medium',
                'query_field': 'event_type',
                'query_value': 'connection_attempt'
            },
            'ddos_attack': {
                'name': 'Potential DDoS Attack',
                'pattern': 'High volume of requests from single source',
                'threshold': 1000,
                'timeframe_minutes': 1,
                'severity': 'critical',
                'query_field': 'event_type',
                'query_value': 'http_request'
            },
            'privilege_escalation': {
                'name': 'Privilege Escalation Attempt',
                'pattern': 'Unauthorized access to elevated resources',
                'threshold': 3,
                'timeframe_minutes': 15,
                'severity': 'critical',
                'query_field': 'event_type',
                'query_value': 'privilege_escalation'
            },
            'malware_signature': {
                'name': 'Known Malware Detected',
                'pattern': 'File hash matches known malware database',
                'threshold': 1,
                'timeframe_minutes': 1,
                'severity': 'critical',
                'query_field': 'event_type',
                'query_value': 'malware_detected'
            },
            'data_exfiltration': {
                'name': 'Suspicious Data Exfiltration',
                'pattern': 'Unusual outbound data transfer',
                'threshold': 500,
                'timeframe_minutes': 5,
                'severity': 'critical',
                'query_field': 'event_type',
                'query_value': 'data_transfer'
            }
        }

    def detect_brute_force(self) -> List[Dict]:
        """Detect brute force login attempts"""
        threats = []
        try:
            query = {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "event_type": "authentication_failed"
                            }
                        },
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": "now-10m"
                                }
                            }
                        }
                    ]
                }
            }

            # Aggregate by source IP
            agg_query = {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "event_type": "authentication_failed"
                            }
                        },
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": "now-10m"
                                }
                            }
                        }
                    ]
                }
            }

            response = self.es.search(
                index="siem-logs-*",
                query=agg_query,
                size=0,
                aggs={
                    "by_source": {
                        "terms": {
                            "field": "src_ip.keyword",
                            "size": 100,
                            "min_doc_count": 5
                        }
                    }
                }
            )

            for bucket in response['aggregations']['by_source']['buckets']:
                if bucket['doc_count'] >= 5:
                    threats.append({
                        'type': 'brute_force_login',
                        'severity': 'high',
                        'source_ip': bucket['key'],
                        'attempt_count': bucket['doc_count'],
                        'detected_at': datetime.utcnow().isoformat(),
                        'description': f"Detected {bucket['doc_count']} failed login attempts from {bucket['key']}"
                    })

        except Exception as e:
            logger.error(f"Error detecting brute force: {e}")

        return threats

    def detect_port_scan(self) -> List[Dict]:
        """Detect port scanning activities"""
        threats = []
        try:
            # Query for connection attempts
            response = self.es.search(
                index="siem-logs-*",
                query={
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "event_type": "connection_attempt"
                                }
                            },
                            {
                                "range": {
                                    "@timestamp": {
                                        "gte": "now-5m"
                                    }
                                }
                            }
                        ]
                    }
                },
                size=0,
                aggs={
                    "by_source": {
                        "terms": {
                            "field": "src_ip.keyword",
                            "size": 100
                        },
                        "aggs": {
                            "unique_ports": {
                                "cardinality": {
                                    "field": "dst_port"
                                }
                            }
                        }
                    }
                }
            )

            for bucket in response['aggregations']['by_source']['buckets']:
                if bucket['unique_ports']['value'] > 20:
                    threats.append({
                        'type': 'port_scan',
                        'severity': 'medium',
                        'source_ip': bucket['key'],
                        'unique_ports': int(bucket['unique_ports']['value']),
                        'detected_at': datetime.utcnow().isoformat(),
                        'description': f"Port scan detected from {bucket['key']}: {int(bucket['unique_ports']['value'])} unique ports"
                    })

        except Exception as e:
            logger.error(f"Error detecting port scan: {e}")

        return threats

    def detect_ddos(self) -> List[Dict]:
        """Detect potential DDoS attacks"""
        threats = []
        try:
            response = self.es.search(
                index="siem-logs-*",
                query={
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "event_type": "http_request"
                                }
                            },
                            {
                                "range": {
                                    "@timestamp": {
                                        "gte": "now-1m"
                                    }
                                }
                            }
                        ]
                    }
                },
                size=0,
                aggs={
                    "by_source": {
                        "terms": {
                            "field": "src_ip.keyword",
                            "size": 100,
                            "min_doc_count": 1000
                        }
                    }
                }
            )

            for bucket in response['aggregations']['by_source']['buckets']:
                if bucket['doc_count'] > 1000:
                    threats.append({
                        'type': 'ddos_attack',
                        'severity': 'critical',
                        'source_ip': bucket['key'],
                        'request_count': bucket['doc_count'],
                        'detected_at': datetime.utcnow().isoformat(),
                        'description': f"DDoS detected: {bucket['doc_count']} requests from {bucket['key']} in last minute"
                    })

        except Exception as e:
            logger.error(f"Error detecting DDoS: {e}")

        return threats

    def publish_threat(self, threat: Dict) -> None:
        """Publish detected threat to Redis and Elasticsearch"""
        try:
            # Store in Redis for real-time alerts
            self.redis.lpush('threats:queue', json.dumps(threat))
            
            # Index in Elasticsearch
            self.es.index(
                index='siem-threats',
                document={
                    '@timestamp': datetime.utcnow().isoformat(),
                    'threat_type': threat['type'],
                    'severity': threat['severity'],
                    'source_ip': threat.get('source_ip'),
                    'description': threat['description'],
                    'details': threat
                }
            )
            
            logger.info(f"Published threat: {threat['type']} from {threat.get('source_ip', 'unknown')}")

        except Exception as e:
            logger.error(f"Error publishing threat: {e}")

    def run(self):
        """Main threat detection loop"""
        logger.info("Starting Threat Detection Engine")

        while True:
            try:
                all_threats = []

                # Run all threat detection methods
                all_threats.extend(self.detect_brute_force())
                all_threats.extend(self.detect_port_scan())
                all_threats.extend(self.detect_ddos())

                # Publish detected threats
                for threat in all_threats:
                    self.publish_threat(threat)

                # Sleep before next iteration
                time.sleep(30)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(30)


def main():
    """Entry point"""
    engine = ThreatDetectionEngine()
    engine.run()


if __name__ == '__main__':
    main()
