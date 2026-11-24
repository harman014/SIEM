"""
Anomaly Detection Engine for AI-SIEM
Detects unusual patterns in network traffic and security events
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import redis
from elasticsearch import Elasticsearch
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

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


class AnomalyDetectionEngine:
    """Detects anomalies in security events using Isolation Forest"""

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

        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False

    def fetch_recent_logs(self, hours: int = 1) -> List[Dict]:
        """Fetch recent logs from Elasticsearch"""
        try:
            query = {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{hours}h",
                                    "lte": "now"
                                }
                            }
                        }
                    ]
                }
            }

            response = self.es.search(
                index="siem-logs-*",
                query=query,
                size=10000
            )

            logs = [hit['_source'] for hit in response['hits']['hits']]
            logger.info(f"Fetched {len(logs)} logs from past {hours} hours")
            return logs

        except Exception as e:
            logger.error(f"Error fetching logs: {e}")
            return []

    def extract_features(self, logs: List[Dict]) -> Tuple[np.ndarray, List[str]]:
        """Extract numerical features from logs for anomaly detection"""
        if not logs:
            return np.array([]), []

        features_list = []
        log_ids = []

        for log in logs:
            try:
                # Extract features
                src_port = int(log.get('src_port', 0)) if log.get('src_port') else 0
                dst_port = int(log.get('dst_port', 0)) if log.get('dst_port') else 0
                packet_count = int(log.get('packet_count', 1)) if log.get('packet_count') else 1
                byte_count = int(log.get('byte_count', 0)) if log.get('byte_count') else 0
                
                # Derive features
                try:
                    bytes_per_packet = byte_count / packet_count if packet_count > 0 else 0
                except:
                    bytes_per_packet = 0

                features = [
                    src_port,
                    dst_port,
                    packet_count,
                    byte_count,
                    bytes_per_packet,
                ]

                features_list.append(features)
                log_ids.append(log.get('_id', ''))

            except Exception as e:
                logger.debug(f"Error extracting features from log: {e}")
                continue

        if features_list:
            return np.array(features_list), log_ids
        return np.array([]), []

    def train_model(self, logs: List[Dict]) -> bool:
        """Train the Isolation Forest model on historical data"""
        try:
            X, _ = self.extract_features(logs)
            
            if X.shape[0] < 10:
                logger.warning(f"Insufficient data to train model: {X.shape[0]} samples")
                return False

            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled)
            self.is_trained = True
            logger.info(f"Model trained on {X.shape[0]} samples")
            return True

        except Exception as e:
            logger.error(f"Error training model: {e}")
            return False

    def detect_anomalies(self, logs: List[Dict]) -> List[Dict]:
        """Detect anomalies in current logs"""
        if not self.is_trained:
            logger.warning("Model not trained yet")
            return []

        try:
            X, log_ids = self.extract_features(logs)
            
            if X.shape[0] == 0:
                return []

            X_scaled = self.scaler.transform(X)
            predictions = self.model.predict(X_scaled)
            anomaly_scores = self.model.score_samples(X_scaled)

            anomalies = []
            for idx, (pred, score) in enumerate(zip(predictions, anomaly_scores)):
                if pred == -1:  # Anomaly detected
                    anomalies.append({
                        'log_id': log_ids[idx],
                        'anomaly_score': float(score),
                        'severity': 'high' if score < -0.5 else 'medium',
                        'detected_at': datetime.utcnow().isoformat(),
                        'original_event': logs[idx]
                    })

            logger.info(f"Detected {len(anomalies)} anomalies")
            return anomalies

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []

    def publish_anomalies(self, anomalies: List[Dict]) -> None:
        """Publish detected anomalies to Redis and Elasticsearch"""
        for anomaly in anomalies:
            try:
                # Store in Redis for real-time alerts
                self.redis.lpush('anomalies:queue', json.dumps(anomaly))
                
                # Index in Elasticsearch
                self.es.index(
                    index='siem-anomalies',
                    document={
                        '@timestamp': datetime.utcnow().isoformat(),
                        'anomaly_score': anomaly['anomaly_score'],
                        'severity': anomaly['severity'],
                        'event': anomaly['original_event']
                    }
                )
                
                logger.info(f"Published anomaly with score {anomaly['anomaly_score']:.3f}")

            except Exception as e:
                logger.error(f"Error publishing anomaly: {e}")

    def run(self):
        """Main detection loop"""
        logger.info("Starting Anomaly Detection Engine")
        
        # Initial training phase
        logger.info("Training model on historical data...")
        historical_logs = self.fetch_recent_logs(hours=24)
        self.train_model(historical_logs)

        # Main detection loop
        while True:
            try:
                # Fetch recent logs
                recent_logs = self.fetch_recent_logs(hours=1)
                
                if recent_logs and self.is_trained:
                    # Detect anomalies
                    anomalies = self.detect_anomalies(recent_logs)
                    
                    # Publish results
                    if anomalies:
                        self.publish_anomalies(anomalies)
                
                # Periodically retrain model (every 6 hours)
                if int(time.time()) % (6 * 3600) == 0:
                    historical_logs = self.fetch_recent_logs(hours=24)
                    self.train_model(historical_logs)

                # Sleep before next iteration
                time.sleep(60)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)


def main():
    """Entry point"""
    engine = AnomalyDetectionEngine()
    engine.run()


if __name__ == '__main__':
    main()
