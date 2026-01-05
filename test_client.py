#!/usr/bin/env python3
"""
Test Client - sendet Requests an Server
"""

from unicodedata import name
import requests
from pathlib import Path
import json 
import socket
import threading
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def listen_for_broadcasts(timeout=30):
    """Hört auf Broadcasts"""
    
    
    logger.info("="*60)
    logger.info("DISCOVERY CLIENT")
    logger.info("="*60)
    logger.info("Listening for broadcasts on port 5001...")
    logger.info(f"Timeout: {timeout} seconds")
    logger.info("="*60)
    
    try:
        sock = socket.socket(socket.AF_INET, socket. SOCK_DGRAM)
        sock.bind(('', 5001))  # Lausche auf Port 5001
        sock.settimeout(timeout)

        while True:
            data, addr = sock.recvfrom(1024)
            
            logger.info(f"\n📥 Received broadcast from {addr[0]}:{addr[1]}")
            logger.info(f"   Raw data: {data}")
            
            try:
                message = json.loads(data.decode())
                logger.info(f"   Parsed:")
                for key, value in message.items():
                    logger.info(f"{key}: {value}")
                
                if message.get('service') == 'test-service': 
                    logger.info(f"\n✅ Found server!")
                    sock.close()
                    logger.info(f"   URL: http://{message['ip']}:{message['port']}")
                    SERVER_URL = f"http://{message['ip']}:{message['port']}"
                    return SERVER_URL
                
            except json.JSONDecodeError:
                logger.error(f"Not JSON data")
    
    except socket.timeout:
        logger.error("\n⏱️  Timeout - no broadcasts received")
    except KeyboardInterrupt:
        logger.error("\n\n⏹️  Stopped")

def discover_server(timeout=10,retries=3):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    request = {"action": "discover", "service": "stedgeai-api"}
    for attempt in range(retries):
        try:
            sock.sendto(
                json.dumps(request).encode(), ('<broadcast>', 5001)  
            )
            data, addr = sock.recvfrom(1024)
            response = json.loads(data.decode())
            
            if response.get("service") == "stedgeai-api":
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

def print_test(name):
    logger.info(f"TEST: {name}")

def test_root(SERVER_URL: str):
    """Test GET /"""
    print_test("GET /")
    
    response = requests.get(f"{SERVER_URL}/")
    
    logger.debug(f"Status: {response.status_code}")
    logger.debug(f"Response: {response.json()}")
    
    assert response.status_code == 200
    logger.info("✅ PASSED")
def test_debug(SERVER_URL: str):
    """Test GET /debug"""
    print_test("GET /debug")
    
    response = requests.get(f"{SERVER_URL}/debug")
    
    logger.debug(f"Status: {response.status_code}")
    logger.debug(f"Response:  {response.json()}")
    
    assert response.status_code == 200
    logger.info("✅ PASSED")
def test_upload(SERVER_URL: str):
    """Test POST /upload"""
    print_test("POST /upload")
    
    # Create dummy file
    test_file = Path('./test_model.tflite')
    test_file.write_bytes(b'fake tflite data' * 100)
    
    logger.info(f"Created test file: {test_file} ({test_file.stat().st_size} bytes)")
    
    # Upload
    with open(test_file, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{SERVER_URL}/upload", files=files)
    
    logger.debug(f"Status: {response.status_code}")
    result = response.json()
    logger.debug(f"Response: {result}")
    
    assert response.status_code == 200
    assert 'filename' in result
    
    logger.info("✅ PASSED")
    return result['filename']

def test_generate(SERVER_URL: str,filename):
    """Test POST /generate"""
    print_test("POST /generate")
    
    payload = {
        'filename': filename,
        'target':  'stm32f4',
        'name': 'test_network'
    }
    
    logger.debug(f"Payload: {payload}")
    
    response = requests.post(f"{SERVER_URL}/generate", json=payload)
    
    logger.debug(f"Status: {response.status_code}")
    result = response.json()
    logger.debug(f"Response:  {result}")
    
    assert response.status_code == 200
    assert result['success'] == True
    
    logger.info("✅ PASSED")
    return result['job_id']

def test_list_outputs(SERVER_URL: str, job_id):
    """Test GET /outputs/{job_id}"""
    print_test(f"GET /outputs/{job_id}")
    
    response = requests.get(f"{SERVER_URL}/outputs/{job_id}")
    
    logger.debug(f"Status: {response.status_code}")
    result = response.json()
    logger.debug(f"Response: {result}")
    
    assert response.status_code == 200
    assert len(result['files']) > 0
    
    logger.info("✅ PASSED")
    return result['files']

def test_download(SERVER_URL: str,job_id, filename):
    """Test GET /download/{job_id}/{filename}"""
    print_test(f"GET /download/{job_id}/{filename}")
    
    response = requests. get(f"{SERVER_URL}/download/{job_id}/{filename}")
    
    logger.debug(f"Status: {response.status_code}")
    logger.debug(f"Content-Type: {response.headers. get('content-type')}")
    logger.debug(f"Size: {len(response.content)} bytes")
    logger.debug(f"Content preview: {response.content[:100]}")
    
    assert response. status_code == 200
    
    logger.info("✅ PASSED")

def server_test(SERVER_URL: str):
    """Run all tests"""
    logger.info("🧪 STARTING TESTS")
    
    try:
        # Test sequence
        test_root(SERVER_URL)
        time.sleep(0.5)
        
        test_debug(SERVER_URL)
        time.sleep(0.5)
        
        filename = test_upload(SERVER_URL)
        time.sleep(0.5)
        
        job_id = test_generate(SERVER_URL, filename)
        time.sleep(0.5)
        
        files = test_list_outputs(SERVER_URL, job_id)
        time.sleep(0.5)
        
        test_download(SERVER_URL, job_id, files[0]['name'])
        
        logger.info("✅ ALL TESTS PASSED!")

    except Exception as e:
        logger.error(f"\n❌ TEST FAILED:  {e}")
        import traceback
        traceback.print_exc()

def check_server_running(SERVER_URL: str):
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
    
def main():
    
    SERVER_URL = None
    SERVER_URL = discover_server()

    
    if input("Press 1 to start tests...") == "1":
        server_test(SERVER_URL)

if __name__ == '__main__':
    main()