import requests
import socket
import json
import time
import logging

from utils.config import DISCOVERY_RETRIES, DISCOVERY_TIMEOUT,SERVICE_NAME

# Standard Python pattern
logger = logging.getLogger(__name__)

def discover_server(timeout=DISCOVERY_TIMEOUT,retries=DISCOVERY_RETRIES):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    request = {"action": "discover", "service": SERVICE_NAME}
    for attempt in range(retries):
        try:
            sock.sendto(
                json.dumps(request).encode(), ('<broadcast>', 5001)  
            )
            data, addr = sock.recvfrom(1024)
            response = json.loads(data.decode())
            
            if response.get("service") == SERVICE_NAME:
                SERVER_URL = f"http://{response['ip']}:{response['port']}"
                print(f"✅ Discovered server at {SERVER_URL}")

                sock.close()
                return SERVER_URL
            
        except socket.timeout:
            logger.error(f"⚠️  No response, retrying... ({attempt + 1}/{retries})")
            if attempt < retries:
                time.sleep(1)
    sock.close()
    return None

def heartbeat(SERVER_URL: str):
    """Check if server is running"""
    logger.info(f"\n🔍 Checking server health...")
    
    try:
        response = requests.get(f"{SERVER_URL}/", timeout=5)
        if response.status_code == 200:
            logger.info(f"✅ Server is healthy!")
            return True
        else: 
            logger.info(f"⚠️  Server responded with {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Cannot connect to server!")
        return False
        
    except requests.exceptions. Timeout:
        logger.error(f"❌ Server timeout!")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error:  {e}")
        return False