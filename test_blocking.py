#!/usr/bin/env python3
"""
Test script for Automated Response System
Simulates various attack scenarios to test blocking mechanisms
"""

import json
import socket
import time
import sys

def send_log_to_logstash(log_data, host='localhost', port=5000):
    """Send log data to Logstash TCP input"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock.sendall((json.dumps(log_data) + '\n').encode())
        sock.close()
        return True
    except Exception as e:
        print(f"Error sending log: {e}")
        return False

def test_brute_force_attack():
    """Simulate brute force attack - should trigger IP block"""
    print("\n=== Test 1: Brute Force Attack ===")
    print("Sending 10 failed authentication attempts from same IP...")
    
    attacker_ip = "192.168.100.50"
    
    for i in range(10):
        log = {
            "event_type": "authentication_failed",
            "src_ip": attacker_ip,
            "dst_ip": "10.0.0.5",
            "username": f"admin_{i}",
            "timestamp": int(time.time()),
            "severity": "high"
        }
        if send_log_to_logstash(log):
            print(f"  ✓ Sent failed login attempt {i+1}/10")
        time.sleep(0.5)
    
    print(f"\n⚠️  Expected action: IP {attacker_ip} should be blocked for 60 minutes")
    print("   Check logs: docker logs ai-siem-response")

def test_port_scan():
    """Simulate port scanning - should trigger port/IP block"""
    print("\n=== Test 2: Port Scanning ===")
    print("Sending connection attempts to multiple ports...")
    
    attacker_ip = "192.168.100.51"
    target_ip = "10.0.0.10"
    
    for port in range(1000, 1025):
        log = {
            "event_type": "connection_attempt",
            "src_ip": attacker_ip,
            "dst_ip": target_ip,
            "src_port": 50000 + port,
            "dst_port": port,
            "protocol": "tcp",
            "timestamp": int(time.time())
        }
        if send_log_to_logstash(log):
            print(f"  ✓ Sent connection attempt to port {port}")
        time.sleep(0.1)
    
    print(f"\n⚠️  Expected action: IP {attacker_ip} should be blocked")
    print("   Check logs: docker logs ai-siem-threat-detector")

def test_ddos_attack():
    """Simulate DDoS attack - should trigger IP and port block"""
    print("\n=== Test 3: DDoS Attack ===")
    print("Sending high volume of requests from single source...")
    
    attacker_ip = "192.168.100.52"
    target_port = 80
    
    print("Sending 100 rapid HTTP requests...")
    for i in range(100):
        log = {
            "event_type": "http_request",
            "src_ip": attacker_ip,
            "dst_ip": "10.0.0.20",
            "dst_port": target_port,
            "method": "GET",
            "path": f"/page{i % 10}",
            "timestamp": int(time.time()),
            "bytes": 1024
        }
        if send_log_to_logstash(log):
            if i % 20 == 0:
                print(f"  ✓ Sent {i+1}/100 requests")
        time.sleep(0.05)
    
    print(f"\n⚠️  Expected action: IP {attacker_ip} should be blocked (critical severity)")
    print(f"   Port {target_port} may also be blocked")
    print("   Block duration: 120 minutes (critical threat)")

def print_verification_steps():
    """Print steps to verify the blocking"""
    print("\n" + "="*60)
    print("VERIFICATION STEPS")
    print("="*60)
    print("""
1. Check Automated Response logs:
   docker logs ai-siem-response --tail 50

2. Check Threat Detection logs:
   docker logs ai-siem-threat-detector --tail 50

3. Check blocked IPs in iptables:
   docker exec ai-siem-response iptables -L SIEM_BLOCK -n -v

4. Query response actions in Elasticsearch:
   curl "localhost:9200/siem-response-actions-*/_search?pretty"

5. Check alerts in Elasticsearch:
   curl "localhost:9200/siem-alerts/_search?pretty"

6. Check current blocking status:
   docker exec ai-siem-response python -c "
from main import AutomatedResponseSystem
import json
system = AutomatedResponseSystem()
print(json.dumps(system.get_status(), indent=2))
"
    """)

def main():
    """Run all tests"""
    print("="*60)
    print("AUTOMATED RESPONSE SYSTEM - TEST SUITE")
    print("="*60)
    print("\nThis script will simulate various attacks to test the")
    print("automated response system's blocking capabilities.")
    print("\nMake sure all services are running:")
    print("  docker-compose ps")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\nTest cancelled.")
        sys.exit(0)
    
    # Run tests
    tests = [
        test_brute_force_attack,
        test_port_scan,
        test_ddos_attack,
    ]
    
    for i, test_func in enumerate(tests, 1):
        try:
            test_func()
            print(f"\n✓ Test {i} completed")
            print("\nWaiting 5 seconds before next test...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n\nTests interrupted by user.")
            break
        except Exception as e:
            print(f"\n✗ Test {i} failed: {e}")
    
    # Print verification steps
    print_verification_steps()
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)
    print("\nNote: It may take 30-60 seconds for threats to be detected")
    print("and blocking actions to be executed.")

if __name__ == "__main__":
    main()
