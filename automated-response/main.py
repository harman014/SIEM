"""
Automated Response System for AI-SIEM
Automatically blocks malicious IPs and ports based on threat alerts
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime, timedelta
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

# Auto-block configuration
AUTO_BLOCK_ENABLED = os.getenv('AUTO_BLOCK_ENABLED', 'true').lower() == 'true'
BLOCK_DURATION_MINUTES = int(os.getenv('BLOCK_DURATION_MINUTES', 60))
DRY_RUN_MODE = os.getenv('DRY_RUN_MODE', 'false').lower() == 'true'


class AutomatedResponseSystem:
    """Automatically responds to security threats by blocking malicious traffic"""

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

        # Track blocked IPs and ports
        self.blocked_ips = {}  # {ip: {'blocked_at': timestamp, 'reason': str, 'alert_id': str}}
        self.blocked_ports = {}  # {port: {'blocked_at': timestamp, 'reason': str}}
        
        # Initialize iptables chain for SIEM blocks
        self._initialize_firewall()

    def _initialize_firewall(self):
        """Initialize custom iptables chain for SIEM blocking"""
        try:
            # Create custom chain for SIEM blocks if it doesn't exist
            if not DRY_RUN_MODE:
                # Check if chain exists
                result = subprocess.run(
                    ['iptables', '-L', 'SIEM_BLOCK', '-n'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    # Create new chain
                    subprocess.run(['iptables', '-N', 'SIEM_BLOCK'], check=True)
                    logger.info("Created SIEM_BLOCK iptables chain")
                    
                    # Add rule to jump to our chain from INPUT
                    subprocess.run(
                        ['iptables', '-I', 'INPUT', '-j', 'SIEM_BLOCK'],
                        check=True
                    )
                    logger.info("Added SIEM_BLOCK to INPUT chain")
                else:
                    logger.info("SIEM_BLOCK chain already exists")
            else:
                logger.info("DRY RUN MODE - Firewall initialization skipped")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to initialize firewall: {e}")
            logger.warning("Running without firewall capabilities - blocks will only be logged")
        except FileNotFoundError:
            logger.warning("iptables not found - running in monitoring mode only")

    def block_ip(self, ip: str, reason: str, alert_id: str, duration_minutes: int = None) -> bool:
        """
        Block an IP address using iptables
        
        Args:
            ip: IP address to block
            reason: Reason for blocking
            alert_id: Associated alert ID
            duration_minutes: How long to block (default: BLOCK_DURATION_MINUTES)
            
        Returns:
            True if successful, False otherwise
        """
        if not AUTO_BLOCK_ENABLED:
            logger.info(f"Auto-block disabled - Would block IP {ip}: {reason}")
            return False
            
        if ip in self.blocked_ips:
            logger.info(f"IP {ip} already blocked")
            return True
            
        duration = duration_minutes or BLOCK_DURATION_MINUTES
        
        try:
            if not DRY_RUN_MODE:
                # Add iptables rule to drop packets from this IP
                subprocess.run(
                    ['iptables', '-I', 'SIEM_BLOCK', '-s', ip, '-j', 'DROP'],
                    check=True
                )
                logger.info(f"✓ BLOCKED IP: {ip} - Reason: {reason}")
            else:
                logger.info(f"[DRY RUN] Would block IP: {ip} - Reason: {reason}")
            
            # Track blocked IP
            block_time = datetime.utcnow()
            self.blocked_ips[ip] = {
                'blocked_at': block_time,
                'unblock_at': block_time + timedelta(minutes=duration),
                'reason': reason,
                'alert_id': alert_id,
                'duration_minutes': duration
            }
            
            # Store in Redis for persistence
            self.redis.hset(
                'blocked_ips',
                ip,
                json.dumps(self.blocked_ips[ip], default=str)
            )
            
            # Log to Elasticsearch
            self._log_block_action({
                'action': 'block_ip',
                'target': ip,
                'reason': reason,
                'alert_id': alert_id,
                'duration_minutes': duration,
                'timestamp': block_time.isoformat(),
                'dry_run': DRY_RUN_MODE
            })
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to block IP {ip}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error blocking IP {ip}: {e}")
            return False

    def block_port(self, port: int, protocol: str = 'tcp', reason: str = '', duration_minutes: int = None) -> bool:
        """
        Block a specific port using iptables
        
        Args:
            port: Port number to block
            protocol: Protocol (tcp/udp)
            reason: Reason for blocking
            duration_minutes: How long to block
            
        Returns:
            True if successful, False otherwise
        """
        if not AUTO_BLOCK_ENABLED:
            logger.info(f"Auto-block disabled - Would block port {port}/{protocol}: {reason}")
            return False
            
        port_key = f"{port}/{protocol}"
        if port_key in self.blocked_ports:
            logger.info(f"Port {port_key} already blocked")
            return True
            
        duration = duration_minutes or BLOCK_DURATION_MINUTES
        
        try:
            if not DRY_RUN_MODE:
                # Add iptables rule to drop packets to this port
                subprocess.run(
                    ['iptables', '-I', 'SIEM_BLOCK', '-p', protocol, '--dport', str(port), '-j', 'DROP'],
                    check=True
                )
                logger.info(f"✓ BLOCKED PORT: {port}/{protocol} - Reason: {reason}")
            else:
                logger.info(f"[DRY RUN] Would block port: {port}/{protocol} - Reason: {reason}")
            
            # Track blocked port
            block_time = datetime.utcnow()
            self.blocked_ports[port_key] = {
                'blocked_at': block_time,
                'unblock_at': block_time + timedelta(minutes=duration),
                'reason': reason,
                'duration_minutes': duration
            }
            
            # Store in Redis
            self.redis.hset(
                'blocked_ports',
                port_key,
                json.dumps(self.blocked_ports[port_key], default=str)
            )
            
            # Log to Elasticsearch
            self._log_block_action({
                'action': 'block_port',
                'target': port_key,
                'reason': reason,
                'duration_minutes': duration,
                'timestamp': block_time.isoformat(),
                'dry_run': DRY_RUN_MODE
            })
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to block port {port_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error blocking port {port_key}: {e}")
            return False

    def unblock_ip(self, ip: str) -> bool:
        """Remove IP block"""
        if ip not in self.blocked_ips:
            logger.warning(f"IP {ip} not in blocked list")
            return False
            
        try:
            if not DRY_RUN_MODE:
                # Remove iptables rule
                subprocess.run(
                    ['iptables', '-D', 'SIEM_BLOCK', '-s', ip, '-j', 'DROP'],
                    check=True
                )
                logger.info(f"✓ UNBLOCKED IP: {ip}")
            else:
                logger.info(f"[DRY RUN] Would unblock IP: {ip}")
            
            # Remove from tracking
            block_info = self.blocked_ips.pop(ip)
            self.redis.hdel('blocked_ips', ip)
            
            # Log to Elasticsearch
            self._log_block_action({
                'action': 'unblock_ip',
                'target': ip,
                'reason': f"Automatic unblock after {block_info['duration_minutes']} minutes",
                'timestamp': datetime.utcnow().isoformat(),
                'dry_run': DRY_RUN_MODE
            })
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to unblock IP {ip}: {e}")
            return False

    def unblock_port(self, port: int, protocol: str = 'tcp') -> bool:
        """Remove port block"""
        port_key = f"{port}/{protocol}"
        if port_key not in self.blocked_ports:
            logger.warning(f"Port {port_key} not in blocked list")
            return False
            
        try:
            if not DRY_RUN_MODE:
                # Remove iptables rule
                subprocess.run(
                    ['iptables', '-D', 'SIEM_BLOCK', '-p', protocol, '--dport', str(port), '-j', 'DROP'],
                    check=True
                )
                logger.info(f"✓ UNBLOCKED PORT: {port_key}")
            else:
                logger.info(f"[DRY RUN] Would unblock port: {port_key}")
            
            # Remove from tracking
            block_info = self.blocked_ports.pop(port_key)
            self.redis.hdel('blocked_ports', port_key)
            
            # Log to Elasticsearch
            self._log_block_action({
                'action': 'unblock_port',
                'target': port_key,
                'reason': f"Automatic unblock after {block_info['duration_minutes']} minutes",
                'timestamp': datetime.utcnow().isoformat(),
                'dry_run': DRY_RUN_MODE
            })
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to unblock port {port_key}: {e}")
            return False

    def check_expired_blocks(self):
        """Check and remove expired blocks"""
        current_time = datetime.utcnow()
        
        # Check expired IP blocks
        expired_ips = []
        for ip, info in self.blocked_ips.items():
            unblock_time = info['unblock_at']
            if isinstance(unblock_time, str):
                unblock_time = datetime.fromisoformat(unblock_time)
            
            if current_time >= unblock_time:
                expired_ips.append(ip)
        
        for ip in expired_ips:
            logger.info(f"Block expired for IP: {ip}")
            self.unblock_ip(ip)
        
        # Check expired port blocks
        expired_ports = []
        for port_key, info in self.blocked_ports.items():
            unblock_time = info['unblock_at']
            if isinstance(unblock_time, str):
                unblock_time = datetime.fromisoformat(unblock_time)
            
            if current_time >= unblock_time:
                expired_ports.append(port_key)
        
        for port_key in expired_ports:
            logger.info(f"Block expired for port: {port_key}")
            port, protocol = port_key.split('/')
            self.unblock_port(int(port), protocol)

    def process_alert(self, alert: Dict) -> bool:
        """
        Process security alert and take appropriate action
        
        Args:
            alert: Alert dictionary from alerting engine
            
        Returns:
            True if action taken, False otherwise
        """
        try:
            severity = alert.get('severity', '').lower()
            alert_type = alert.get('type', '')
            threat_type = alert.get('threat_type', '')
            source_ip = alert.get('source_ip')
            dst_port = alert.get('dst_port')
            alert_id = alert.get('alert_id', '')
            
            # Determine action based on severity and type
            action_taken = False
            
            # Block IP for critical/high severity threats
            if severity in ['critical', 'high'] and source_ip:
                reason = f"{severity.upper()} threat: {threat_type or alert_type}"
                
                # Longer block duration for critical threats
                duration = BLOCK_DURATION_MINUTES * 2 if severity == 'critical' else BLOCK_DURATION_MINUTES
                
                if self.block_ip(source_ip, reason, alert_id, duration):
                    action_taken = True
                    logger.info(f"Automatic response: Blocked IP {source_ip} for {duration} minutes")
            
            # Block port for port scan or DDoS attacks
            if threat_type in ['port_scan', 'ddos_attack'] and dst_port:
                reason = f"Protecting against {threat_type}"
                if self.block_port(dst_port, 'tcp', reason, 30):
                    action_taken = True
                    logger.info(f"Automatic response: Blocked port {dst_port} for 30 minutes")
            
            return action_taken
            
        except Exception as e:
            logger.error(f"Error processing alert: {e}")
            return False

    def _log_block_action(self, action_data: Dict):
        """Log block/unblock actions to Elasticsearch"""
        try:
            action_data['@timestamp'] = action_data.get('timestamp', datetime.utcnow().isoformat())
            action_data['service'] = 'automated-response'
            
            self.es.index(
                index=f"siem-response-actions-{datetime.utcnow().strftime('%Y.%m.%d')}",
                document=action_data
            )
        except Exception as e:
            logger.error(f"Failed to log block action to Elasticsearch: {e}")

    def monitor_alerts(self):
        """Monitor Redis for new alerts and respond automatically"""
        logger.info("Starting automated response monitoring...")
        logger.info(f"Auto-block: {'ENABLED' if AUTO_BLOCK_ENABLED else 'DISABLED'}")
        logger.info(f"Mode: {'DRY RUN (logging only)' if DRY_RUN_MODE else 'ACTIVE (blocking enabled)'}")
        logger.info(f"Default block duration: {BLOCK_DURATION_MINUTES} minutes")
        
        pubsub = self.redis.pubsub()
        pubsub.subscribe('alerts')
        
        logger.info("Subscribed to 'alerts' channel, waiting for alerts...")
        
        last_cleanup = time.time()
        
        for message in pubsub.listen():
            try:
                # Check for expired blocks every 60 seconds
                if time.time() - last_cleanup > 60:
                    self.check_expired_blocks()
                    last_cleanup = time.time()
                
                # Process new alerts
                if message['type'] == 'message':
                    alert_data = json.loads(message['data'])
                    logger.info(f"Received alert: {alert_data.get('alert_id')} - {alert_data.get('severity')}")
                    
                    if self.process_alert(alert_data):
                        logger.info(f"Automatic response executed for alert {alert_data.get('alert_id')}")
                    else:
                        logger.debug(f"No automatic action taken for alert {alert_data.get('alert_id')}")
                        
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode alert message: {e}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    def get_status(self) -> Dict:
        """Get current blocking status"""
        return {
            'auto_block_enabled': AUTO_BLOCK_ENABLED,
            'dry_run_mode': DRY_RUN_MODE,
            'blocked_ips_count': len(self.blocked_ips),
            'blocked_ports_count': len(self.blocked_ports),
            'blocked_ips': list(self.blocked_ips.keys()),
            'blocked_ports': list(self.blocked_ports.keys()),
            'block_duration_minutes': BLOCK_DURATION_MINUTES
        }


def main():
    """Main function"""
    logger.info("=== AI-SIEM Automated Response System ===")
    
    try:
        response_system = AutomatedResponseSystem()
        
        # Print current status
        status = response_system.get_status()
        logger.info(f"Status: {json.dumps(status, indent=2)}")
        
        # Start monitoring alerts
        response_system.monitor_alerts()
        
    except KeyboardInterrupt:
        logger.info("Shutting down automated response system...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
