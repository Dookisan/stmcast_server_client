import logging
import socket
import json
from config import GenerateRequest, UPLOAD_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def discovery_server():
    """
    Listen for discovery requests and respond
    
    Protocol:
      Client sends (broadcast):   {"action": "discover", "service":  "stedgeai-api"}
      Server responds (unicast):  {"service": "stedgeai-api", "ip": "192.168.1.100", "port": 5000}
    """
    
   
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    # Bind to discovery port
    sock.bind(('', 5001))
        
    local_ip = get_local_ip()

    while True:
        try:
            data,client_addr = sock.recvfrom(1024)

            try:
                request = json.loads(data.decode())
                logger.info(f"\n📥 Received discovery request from {client_addr[0]}:{client_addr[1]}")
                logger.info(f"   Request data: {request}")

                action = request.get('action')
                service = request.get('service')

                if action == 'discover' and service == 'stedgeai-api':
                    response = {
                        'service': 'stedgeai-api',
                        'ip': local_ip,
                        'port': 5000
                    }
                    response_data = json.dumps(response).encode()
                    sock.sendto(response_data, client_addr)
                    logger.info(f"📤 Sent discovery response to {client_addr[0]}:{client_addr[1]}")
                    logger.info(f"   Response data: {response}")
            except json.JSONDecodeError:
                logger.warning(f"Received non-JSON data from {client_addr[0]}:{client_addr[1]}")
        except Exception as e:
            logger.error(f"Error: {e}")