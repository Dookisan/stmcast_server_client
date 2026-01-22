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
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Enable broadcast reception
    
    # Try to enable SO_REUSEPORT if available (helps on some platforms)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except (AttributeError, OSError):
        pass  # Not available on Windows
        
    # Try to bind to discovery port, with fallback ports
    discovery_port = 5001
    ports_to_try = [5001, 5002, 5003, 5004, 5005]
    
    for port in ports_to_try:
        try:
            sock.bind(('', port))  # Bind to all interfaces
            discovery_port = port
            logger.info(f"✅ Discovery server bound to port {port}")
            break
        except OSError as e:
            logger.warning(f"⚠️ Could not bind to port {port}: {e}")
            if port == ports_to_try[-1]:
                logger.error("❌ Failed to bind to any discovery port. Discovery service unavailable.")
                return
    
    logger.info(f"🌐 Discovery server bound and listening on port {discovery_port}")

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
                    # Determine the server IP that is reachable by the client
                    try:
                        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        temp_sock.connect((client_addr[0], 1))
                        local_ip_for_client = temp_sock.getsockname()[0]
                        temp_sock.close()
                    except Exception:
                        # Fallback to configured method if determination fails
                        local_ip_for_client = get_local_ip()

                    response = {
                        'service': 'stedgeai-api',
                        'ip': local_ip_for_client,
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