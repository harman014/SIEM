"""
Alerting Engine for AI-SIEM
Processes detected anomalies and threats, generates alerts
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

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


class AlertingEngine:
    """Processes threats and anomalies, generates alerts"""

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

        # Alert configuration
        self.alert_rules = self._load_alert_rules()

    def _load_alert_rules(self) -> Dict[str, Dict]:
        """Load alert rules configuration"""
        return {
            'critical_threat': {
                'condition': lambda alert: alert.get('severity') == 'critical',
                'action': ['elasticsearch', 'redis_channel'],
                'escalate': True
            },
            'high_anomaly': {
                'condition': lambda alert: alert.get('anomaly_score', 0) < -0.5,
                'action': ['elasticsearch', 'redis_channel'],
                'escalate': False
            },
            'multiple_failed_logins': {
                'condition': lambda alert: alert.get('attempt_count', 0) > 5,
                'action': ['elasticsearch', 'redis_channel'],
                'escalate': True
            }
        }

    def process_threat_alert(self, threat: Dict) -> Optional[Dict]:
        """Process threat and create alert"""
        try:
            alert = {
                'alert_id': f"threat-{int(time.time() * 1000)}",
                'type': 'threat',
                'threat_type': threat.get('type'),
                'severity': threat.get('severity'),
                'source_ip': threat.get('source_ip'),
                'description': threat.get('description'),
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'open',
                'source': threat
            }

            return alert

        except Exception as e:
            logger.error(f"Error processing threat alert: {e}")
            return None

    def process_anomaly_alert(self, anomaly: Dict) -> Optional[Dict]:
        """Process anomaly and create alert"""
        try:
            alert = {
                'alert_id': f"anomaly-{int(time.time() * 1000)}",
                'type': 'anomaly',
                'anomaly_score': anomaly.get('anomaly_score'),
                'severity': anomaly.get('severity'),
                'description': f"Anomaly detected with score {anomaly.get('anomaly_score'):.3f}",
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'open',
                'source': anomaly
            }

            return alert

        except Exception as e:
            logger.error(f"Error processing anomaly alert: {e}")
            return None

    def evaluate_rules(self, alert: Dict) -> bool:
        """Evaluate if alert matches any rules"""
        for rule_name, rule_config in self.alert_rules.items():
            try:
                if rule_config['condition'](alert):
                    logger.info(f"Alert matched rule: {rule_name}")
                    return True
            except Exception as e:
                logger.debug(f"Error evaluating rule {rule_name}: {e}")

        return False

    def store_alert(self, alert: Dict) -> None:
        """Store alert in Elasticsearch"""
        try:
            self.es.index(
                index='siem-alerts',
                document=alert
            )
            logger.info(f"Stored alert: {alert['alert_id']}")

        except Exception as e:
            logger.error(f"Error storing alert: {e}")

    def publish_alert(self, alert: Dict) -> None:
        """Publish alert to Redis channel for real-time notifications"""
        try:
            # Publish to Redis channel for automated response system
            self.redis.publish('alerts', json.dumps(alert))
            
            # Also publish to legacy channel
            self.redis.publish('siem:alerts', json.dumps(alert))
            
            # Also push to alerts queue for processing
            self.redis.lpush('alerts:queue', json.dumps(alert))
            
            logger.info(f"Published alert to Redis: {alert['alert_id']}")

        except Exception as e:
            logger.error(f"Error publishing alert: {e}")

    def deduplicate_alert(self, alert: Dict, window_seconds: int = 300) -> bool:
        """Check if similar alert was recently triggered"""
        try:
            # Create a cache key based on alert characteristics
            if alert['type'] == 'threat':
                cache_key = f"alert:threat:{alert.get('threat_type')}:{alert.get('source_ip')}"
            else:
                cache_key = f"alert:anomaly:{int(alert.get('anomaly_score', 0) * 100)}"

            # Check if exists in Redis
            exists = self.redis.exists(cache_key)
            
            if not exists:
                # Set with TTL to prevent duplicate alerts within window
                self.redis.setex(cache_key, window_seconds, '1')
                return False
            else:
                logger.debug(f"Alert deduplicated: {cache_key}")
                return True

        except Exception as e:
            logger.error(f"Error deduplicating alert: {e}")
            return False

    def process_queue(self):
        """Process threat and anomaly queues"""
        try:
            # Process threats
            while True:
                threat_data = self.redis.rpop('threats:queue')
                if not threat_data:
                    break

                try:
                    threat = json.loads(threat_data)
                    alert = self.process_threat_alert(threat)
                    
                    if alert and not self.deduplicate_alert(alert):
                        if self.evaluate_rules(alert):
                            self.store_alert(alert)
                            self.publish_alert(alert)

                except Exception as e:
                    logger.error(f"Error processing threat: {e}")

            # Process anomalies
            while True:
                anomaly_data = self.redis.rpop('anomalies:queue')
                if not anomaly_data:
                    break

                try:
                    anomaly = json.loads(anomaly_data)
                    alert = self.process_anomaly_alert(anomaly)
                    
                    if alert and not self.deduplicate_alert(alert):
                        if self.evaluate_rules(alert):
                            self.store_alert(alert)
                            self.publish_alert(alert)

                except Exception as e:
                    logger.error(f"Error processing anomaly: {e}")

        except Exception as e:
            logger.error(f"Error processing queues: {e}")

    def run(self):
        """Main alerting loop"""
        logger.info("Starting Alerting Engine")

        while True:
            try:
                self.process_queue()
                time.sleep(5)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)


def main():
    """Entry point"""
    engine = AlertingEngine()
    engine.run()


if __name__ == '__main__':
    main()
