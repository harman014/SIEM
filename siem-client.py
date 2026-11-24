#!/usr/bin/env python3
"""
API Client for AI-SIEM
Query detection results and manage system
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class SIEMClient:
    """Client for interacting with AI-SIEM"""

    def __init__(self, es_host: str = 'localhost', es_port: int = 9200, 
                 username: str = 'elastic', password: str = 'change_me'):
        self.es_url = f"http://{es_host}:{es_port}"
        self.username = username
        self.password = password
        self.auth = (username, password)

    def get_recent_alerts(self, hours: int = 1, limit: int = 100) -> List[Dict]:
        """Fetch recent alerts"""
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": f"now-{hours}h"
                    }
                }
            },
            "sort": [{"@timestamp": {"order": "desc"}}],
            "size": limit
        }
        
        response = requests.get(
            f"{self.es_url}/siem-alerts-*/_search",
            json=query,
            auth=self.auth
        )
        
        if response.status_code == 200:
            hits = response.json()['hits']['hits']
            return [hit['_source'] for hit in hits]
        return []

    def get_recent_threats(self, hours: int = 1, severity: Optional[str] = None) -> List[Dict]:
        """Fetch detected threats"""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{hours}h"
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        if severity:
            query["query"]["bool"]["must"].append({
                "match": {"severity": severity}
            })
        
        response = requests.get(
            f"{self.es_url}/siem-threats-*/_search",
            json=query,
            auth=self.auth
        )
        
        if response.status_code == 200:
            hits = response.json()['hits']['hits']
            return [hit['_source'] for hit in hits]
        return []

    def get_anomalies(self, hours: int = 1) -> List[Dict]:
        """Fetch detected anomalies"""
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": f"now-{hours}h"
                    }
                }
            },
            "sort": [{"anomaly_score": {"order": "asc"}}],
            "size": 100
        }
        
        response = requests.get(
            f"{self.es_url}/siem-anomalies-*/_search",
            json=query,
            auth=self.auth
        )
        
        if response.status_code == 200:
            hits = response.json()['hits']['hits']
            return [hit['_source'] for hit in hits]
        return []

    def search_logs(self, query_string: str, hours: int = 24) -> List[Dict]:
        """Search raw logs"""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "query": query_string
                            }
                        },
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{hours}h"
                                }
                            }
                        }
                    ]
                }
            },
            "size": 100
        }
        
        response = requests.get(
            f"{self.es_url}/siem-logs-*/_search",
            json=query,
            auth=self.auth
        )
        
        if response.status_code == 200:
            hits = response.json()['hits']['hits']
            return [hit['_source'] for hit in hits]
        return []

    def get_stats(self) -> Dict:
        """Get system statistics"""
        stats = {
            "cluster_health": None,
            "indices": [],
            "document_count": {}
        }
        
        # Cluster health
        try:
            resp = requests.get(
                f"{self.es_url}/_cluster/health",
                auth=self.auth
            )
            stats["cluster_health"] = resp.json()
        except:
            pass
        
        # Index stats
        indices = ["siem-logs-*", "siem-threats-*", "siem-anomalies-*", "siem-alerts-*"]
        for idx in indices:
            try:
                resp = requests.get(
                    f"{self.es_url}/{idx}/_count",
                    auth=self.auth
                )
                if resp.status_code == 200:
                    stats["document_count"][idx] = resp.json()['count']
            except:
                pass
        
        return stats

    def get_high_severity_alerts(self, hours: int = 24) -> List[Dict]:
        """Get critical and high severity alerts"""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "terms": {
                                "severity": ["critical", "high"]
                            }
                        },
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{hours}h"
                                }
                            }
                        }
                    ]
                }
            },
            "size": 50
        }
        
        response = requests.get(
            f"{self.es_url}/siem-alerts-*/_search",
            json=query,
            auth=self.auth
        )
        
        if response.status_code == 200:
            hits = response.json()['hits']['hits']
            return [hit['_source'] for hit in hits]
        return []


def print_alerts(alerts: List[Dict]):
    """Pretty print alerts"""
    if not alerts:
        print("No alerts found")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(alerts)} alert(s)")
    print(f"{'='*80}\n")
    
    for alert in alerts[:10]:  # Show first 10
        print(f"Alert ID: {alert.get('alert_id', 'N/A')}")
        print(f"Type: {alert.get('type', 'N/A')}")
        print(f"Severity: {alert.get('severity', 'N/A')}")
        print(f"Timestamp: {alert.get('timestamp', alert.get('@timestamp', 'N/A'))}")
        print(f"Description: {alert.get('description', 'N/A')}")
        print("-" * 80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='AI-SIEM CLI Client')
    parser.add_argument('--command', choices=['alerts', 'threats', 'anomalies', 'stats', 'high-severity'],
                       default='stats', help='Command to execute')
    parser.add_argument('--hours', type=int, default=24, help='Time range in hours')
    parser.add_argument('--severity', help='Filter by severity')
    
    args = parser.parse_args()
    
    client = SIEMClient()
    
    try:
        if args.command == 'alerts':
            alerts = client.get_recent_alerts(hours=args.hours)
            print_alerts(alerts)
        
        elif args.command == 'threats':
            threats = client.get_recent_threats(hours=args.hours, severity=args.severity)
            print_alerts(threats)
        
        elif args.command == 'anomalies':
            anomalies = client.get_anomalies(hours=args.hours)
            print_alerts(anomalies)
        
        elif args.command == 'high-severity':
            alerts = client.get_high_severity_alerts(hours=args.hours)
            print_alerts(alerts)
        
        elif args.command == 'stats':
            stats = client.get_stats()
            print("\nSystem Statistics:")
            print(f"Cluster Health: {stats['cluster_health']['status']}")
            print("\nDocument Counts:")
            for idx, count in stats['document_count'].items():
                print(f"  {idx}: {count}")
    
    except Exception as e:
        print(f"Error: {e}")
