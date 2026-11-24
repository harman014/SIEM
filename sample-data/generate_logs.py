#!/usr/bin/env python3
"""
Sample Log Generator for AI-SIEM Testing
Generates realistic security events for testing detection engines
"""

import socket
import json
import time
import random
import argparse
from datetime import datetime
from typing import Dict

class LogGenerator:
    """Generates test security events"""

    def __init__(self, host: str = 'localhost', port: int = 5000):
        self.host = host
        self.port = port

    def send_event(self, event: Dict) -> bool:
        """Send single event to Logstash"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            sock.sendall((json.dumps(event) + '\n').encode())
            sock.close()
            return True
        except Exception as e:
            print(f"Error sending event: {e}")
            return False

    def generate_normal_traffic(self, count: int = 50):
        """Generate normal network traffic"""
        print(f"Generating {count} normal traffic events...")
        common_ips = [
            "192.168.1.100", "192.168.1.101", "192.168.1.102",
            "10.0.0.1", "10.0.0.2"
        ]
        common_ports = [80, 443, 22, 3306, 5432, 8080]
        common_destinations = [
            "1.1.1.1", "8.8.8.8", "10.0.0.50", "172.16.0.1"
        ]

        for i in range(count):
            event = {
                "@timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": "normal_traffic",
                "src_ip": random.choice(common_ips),
                "dst_ip": random.choice(common_destinations),
                "src_port": random.randint(10000, 65535),
                "dst_port": random.choice(common_ports),
                "packet_count": random.randint(10, 500),
                "byte_count": random.randint(1000, 500000),
                "protocol": random.choice(["tcp", "udp"]),
                "severity": "low"
            }
            if self.send_event(event):
                print(f"  ✓ Event {i+1}/{count}")
            time.sleep(0.1)

    def generate_brute_force_attack(self, source_ip: str = "192.168.1.50", count: int = 10):
        """Generate brute force login attempts"""
        print(f"Generating {count} failed login attempts from {source_ip}...")
        target_ips = ["10.0.0.5", "10.0.0.10"]

        for i in range(count):
            event = {
                "@timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": "authentication_failed",
                "src_ip": source_ip,
                "dst_ip": random.choice(target_ips),
                "src_port": random.randint(10000, 65535),
                "dst_port": 22,
                "user": "admin",
                "protocol": "ssh",
                "severity": "high",
                "reason": "invalid_credentials"
            }
            if self.send_event(event):
                print(f"  ✓ Failed login {i+1}/{count}")
            time.sleep(0.5)

    def generate_port_scan(self, source_ip: str = "192.168.1.75", ports: int = 30):
        """Generate port scanning activity"""
        print(f"Generating port scan from {source_ip} ({ports} ports)...")
        target = "10.0.0.100"

        for port in range(1000, 1000 + ports):
            event = {
                "@timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": "connection_attempt",
                "src_ip": source_ip,
                "dst_ip": target,
                "src_port": random.randint(10000, 65535),
                "dst_port": port,
                "packet_count": 1,
                "byte_count": 64,
                "severity": "medium",
                "status": "connection_refused"
            }
            if self.send_event(event):
                print(f"  ✓ Port {port}")
            time.sleep(0.1)

    def generate_ddos_attack(self, source_ip: str = "192.168.1.90", duration_seconds: int = 10):
        """Generate DDoS-like traffic pattern"""
        print(f"Generating DDoS from {source_ip} for {duration_seconds} seconds...")
        target = "10.0.0.50"
        start_time = time.time()
        event_count = 0

        while time.time() - start_time < duration_seconds:
            for _ in range(20):  # 20 events per iteration
                event = {
                    "@timestamp": datetime.utcnow().isoformat() + "Z",
                    "event_type": "http_request",
                    "src_ip": source_ip,
                    "dst_ip": target,
                    "src_port": random.randint(10000, 65535),
                    "dst_port": 80,
                    "packet_count": 1,
                    "byte_count": random.randint(200, 500),
                    "severity": "critical",
                    "http_method": random.choice(["GET", "POST", "HEAD"]),
                    "http_status": 200
                }
                if self.send_event(event):
                    event_count += 1
            
            print(f"  ✓ Sent {event_count} requests ({int(time.time() - start_time)}s)")
            time.sleep(0.5)

    def generate_data_exfiltration(self, count: int = 5):
        """Generate suspicious data transfer"""
        print(f"Generating {count} data exfiltration events...")
        internal_ips = ["192.168.1.200", "192.168.1.201"]
        external_ips = ["203.0.113.1", "198.51.100.1", "192.0.2.1"]

        for i in range(count):
            event = {
                "@timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": "data_transfer",
                "src_ip": random.choice(internal_ips),
                "dst_ip": random.choice(external_ips),
                "src_port": random.randint(10000, 65535),
                "dst_port": 443,
                "packet_count": 1000,
                "byte_count": random.randint(100000000, 500000000),  # 100MB - 500MB
                "protocol": "tcp",
                "severity": "critical",
                "direction": "outbound"
            }
            if self.send_event(event):
                print(f"  ✓ Exfil event {i+1}/{count}")
            time.sleep(1)

    def generate_privilege_escalation(self, count: int = 3):
        """Generate privilege escalation attempts"""
        print(f"Generating {count} privilege escalation attempts...")
        users = ["user1", "user2", "guest"]

        for i in range(count):
            event = {
                "@timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": "privilege_escalation",
                "src_ip": f"192.168.1.{random.randint(100, 200)}",
                "dst_ip": "10.0.0.10",
                "src_port": random.randint(10000, 65535),
                "dst_port": 22,
                "user": random.choice(users),
                "target_user": "root",
                "severity": "critical",
                "method": random.choice(["sudo", "su", "runAs"])
            }
            if self.send_event(event):
                print(f"  ✓ Escalation attempt {i+1}/{count}")
            time.sleep(1)

    def run_full_test_scenario(self):
        """Run complete test scenario"""
        print("\n" + "="*60)
        print("AI-SIEM Test Data Generation - Full Scenario")
        print("="*60 + "\n")

        # Generate normal baseline
        self.generate_normal_traffic(50)
        
        print("\n⏳ Waiting 5 seconds before attack simulation...\n")
        time.sleep(5)

        # Simulate attacks
        self.generate_brute_force_attack(count=8)
        print()
        
        self.generate_port_scan(ports=25)
        print()
        
        self.generate_data_exfiltration(count=3)
        print()
        
        self.generate_ddos_attack(duration_seconds=5)
        print()
        
        self.generate_privilege_escalation(count=2)

        print("\n" + "="*60)
        print("✓ Test scenario complete!")
        print("  Check Kibana: http://localhost:5601")
        print("  Check Grafana: http://localhost:3000")
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Generate test security events for AI-SIEM'
    )
    parser.add_argument('--host', default='localhost', help='Logstash host')
    parser.add_argument('--port', type=int, default=5000, help='Logstash port')
    parser.add_argument('--scenario', default='full', 
                       choices=['full', 'normal', 'bruteforce', 'portscan', 'ddos', 'exfil', 'escalation'],
                       help='Test scenario to run')
    parser.add_argument('--count', type=int, default=10, help='Event count for specific scenarios')

    args = parser.parse_args()

    generator = LogGenerator(args.host, args.port)

    try:
        if args.scenario == 'full':
            generator.run_full_test_scenario()
        elif args.scenario == 'normal':
            generator.generate_normal_traffic(args.count)
        elif args.scenario == 'bruteforce':
            generator.generate_brute_force_attack(count=args.count)
        elif args.scenario == 'portscan':
            generator.generate_port_scan(ports=args.count)
        elif args.scenario == 'ddos':
            generator.generate_ddos_attack(duration_seconds=args.count)
        elif args.scenario == 'exfil':
            generator.generate_data_exfiltration(count=args.count)
        elif args.scenario == 'escalation':
            generator.generate_privilege_escalation(count=args.count)

    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == '__main__':
    main()
