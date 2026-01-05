import logging
from os import name
from time import time
from unittest import result
from urllib import response 
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class TestSuite:
    def __init__(self, SERVER_URL: str):

        self.SERVER_URL = SERVER_URL
        self.job_id = None
        self.filename = None
        self.files = None

    def server_test(self):
        """Run all tests"""
        logger.info("🧪 STARTING TESTS")
    
        try:
            # Test sequence
            self.test_root()
            self.test_debug()
            self.test_upload()
            self.test_generate()
            self.test_list_outputs()
            self.test_download()
        
            logger.info("✅ ALL TESTS PASSED!")

        except Exception as e:
            logger.error(f"\n❌ TEST FAILED:  {e}")
            import traceback
            traceback.print_exc()

    def print_test(self, name):
        logger.info(f"TEST: {name}")

    def test_root(self):
        """Test GET /"""
        self.print_test("GET /")
    
        response = requests.get(f"{self.SERVER_URL}/")
    
        logger.debug(f"Status: {response.status_code}")
        logger.debug(f"Response: {response.json()}")
    
        assert response.status_code == 200
        logger.info("✅ PASSED")
        
    def test_debug(self):
        """Test GET /debug"""
        self.print_test("GET /debug")
    
        response = requests.get(f"{self.SERVER_URL}/debug")
    
        logger.debug(f"Status: {response.status_code}")
        logger.debug(f"Response:  {response.json()}")
    
        assert response.status_code == 200
        logger.info("✅ PASSED")
        
    def test_upload(self):
        """Test POST /upload"""
        self.print_test("POST /upload")
    
        # Create dummy file
        test_file = Path('./test_model.tflite') #TODO: make path dynamic
        test_file.write_bytes(b'fake tflite data' * 100)
    
        logger.info(f"Created test file: {test_file} ({test_file.stat().st_size} bytes)")
    
        # Upload
        with open(test_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{self.SERVER_URL}/upload", files=files)
    
        logger.debug(f"Status: {response.status_code}")
        result = response.json()
        logger.debug(f"Response: {result}")
    
        assert response.status_code == 200
        assert 'filename' in result
    
        logger.info("✅ PASSED")
        self.filename = result['filename']
    
    def test_generate(self):
        """Test POST /generate"""
        self.print_test("POST /generate")
    
        payload = {
        'filename': self.filename,
        'target':  'stm32f4',
        'name': 'test_network'
        }
    
        logger.debug(f"Payload: {payload}")
    
        response = requests.post(f"{self.SERVER_URL}/generate", json=payload)
    
        logger.debug(f"Status: {response.status_code}")
        result = response.json()
        logger.debug(f"Response:  {result}")
    
        assert response.status_code == 200
        assert result['success'] == True
    
        logger.info("✅ PASSED")
        self.job_id = result['job_id']
    

    def test_list_outputs(self):
        """Test GET /outputs/{job_id}"""
        self.print_test(f"GET /outputs/{self.job_id}")
        
        response = requests.get(f"{self.SERVER_URL}/outputs/{self.job_id}")
    
        logger.debug(f"Status: {response.status_code}")
        result = response.json()
        logger.debug(f"Response: {result}")
    
        assert response.status_code == 200
        assert len(result['files']) > 0
    
        logger.info("✅ PASSED")
        self.files = result['files'][0]
    
    def test_download(self):
        """Test GET /download/{job_id}/{filename}"""
        self.print_test(f"GET /download/{self.job_id}/{self.files['name']}")
        
        response = requests.get(f"{self.SERVER_URL}/download/{self.job_id}/{self.files['name']}")
        logger.debug(f"Downloading file: {self.files['name']}")
        logger.debug(f"Status: {response.status_code}")
        logger.debug(f"Content-Type: {response.headers.get('content-type')}")
        logger.debug(f"Size: {len(response.content)} bytes")
        logger.debug(f"Content preview: {response.content[:100]}")
    
        assert response.status_code == 200
    
        logger.info("✅ PASSED")