#!/usr/bin/env python3
"""
Minimal Server mit MAXIMALEN Debug Outputs
Siehst GENAU was bei jedem Request passiert
"""

import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import time
import uvicorn
import socket
import threading
from contextlib import asynccontextmanager
import logging
import sys

logger = logging.getLogger(__name__)

def setup_logging(level=logging.INFO):
    """Setup logging configuration"""
    
    # Console Handler (colored for terminal)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # File Handler (all logs)
    file_handler = logging. FileHandler('server.log')
    file_handler.setLevel(logging.DEBUG)
    
    # Formatters
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)-8s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    file_format = logging. Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    console_handler.setFormatter(console_format)
    file_handler.setFormatter(file_format)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    logger.info("Logging configured")
# ============================================================================
# CONFIG
# ============================================================================

UPLOAD_DIR = Path('./uploads')
OUTPUT_DIR = Path('./outputs')

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================================
# MODELS
# ============================================================================

class GenerateRequest(BaseModel):
    filename: str
    target: str = "stm32f4"
    name: str = "network"

# ============================================================================
# HELPER MIT DEBUG PRINTS
# ============================================================================


def print_request_start(endpoint, method="POST"):
    print("\n")
    print(f"🔵 REQUEST START:   {method} {endpoint}")
    print(f"🔵 Time: {datetime.now().strftime('%H:%M:%S')}")
   
def print_request_end(endpoint):
    print(f"✅ REQUEST END: {endpoint}")

#=============================================================================
# Network scan
#=============================================================================

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def broadcast_loop():
    """Sendet Broadcasts"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket. SOL_SOCKET, socket. SO_BROADCAST, 1)
    
    message = json.dumps({
        'service': 'test-service',
        'ip': get_local_ip(),
        'port': 5000,
        'timestamp': datetime.now().isoformat()
    }).encode()
    
    logger.info(f"📡 Broadcasting:  {message.decode()}")
    
    while True:
        try:
            sock.sendto(message, ('<broadcast>', 5001))
            logger.info(f"   Sent broadcast at {datetime.now().strftime('%H:%M:%S')}")
            time.sleep(5)
        except Exception as e: 
            logger.error(f"Error:  {e}")
            break

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
            
        


# Get local IP address
# ============================================================================
# ENDPOINTS
# ============================================================================

# ============================================================================
# STARTUP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager
    Code BEFORE yield = startup
    Code AFTER yield = shutdown
    """

    # ===== STARTUP =====
  
    logger.info("🚀 STEdgeAI SERVER STARTING")
    
    logger.debug(f"Upload folder: {UPLOAD_DIR.absolute()}")
    logger.debug(f"Output folder:  {OUTPUT_DIR.absolute()}")
    logger.info(f"Local IP: {get_local_ip()}")
    logger.debug(f"")
    logger.info(f"📖 Interactive Docs: http://localhost:5000/docs")
    logger.info(f"🔍 Debug Endpoint: http://localhost:5000/debug")
   
    
    # START BROADCAST THREAD
    logger.info("📡 Starting discovery broadcast thread...")
    broadcast_thread = threading.Thread(target=discovery_server, daemon=True)
    broadcast_thread.start()
    logger.info("✅ Discovery broadcast started on port 5001\n")
    
    yield  
    
    # ===== SHUTDOWN =====
    
    print("🛑 SERVER SHUTTING DOWN")
    
    # Cleanup code hier (falls nötig)

app = FastAPI(
    title="Debug Server",
    lifespan=lifespan  # ← Übergebe lifespan hier!
)

@app.get("/")
def root():
    """Simplest endpoint"""
    print_request_start("/", "GET")
    
    logger.info("🔵 Function:  root()")
    logger.debug("🔵 Returning JSON dict")
    
    response = {"message": "Server running", "docs":  "/docs"}
    logger.debug(f"🔵 Response: {response}")
    
    print_request_end("/")
    return response


@app.get("/debug")
def debug():
    """Debug endpoint - zeigt Dateien"""
    print_request_start("/debug", "GET")
    
    # Liste uploads
    uploads = list(UPLOAD_DIR.glob('*'))
    logger.debug(f"🔵 Uploads folder: {UPLOAD_DIR. absolute()}")
    logger.debug(f"🔵 Found {len(uploads)} files:")
    for f in uploads:
        logger.debug(f"   - {f.name} ({f.stat().st_size} bytes)")
    
    # Liste outputs
    outputs = list(OUTPUT_DIR.glob('*'))
    logger.debug(f"🔵 Outputs folder: {OUTPUT_DIR.absolute()}")
    logger.debug(f"🔵 Found {len(outputs)} folders:")
    for f in outputs: 
        logger.debug(f"   - {f.name}")
    
    response = {
        "uploads": [f.name for f in uploads],
        "outputs": [f.name for f in outputs]
    }
    
    logger.debug(f"🔵 Response:  {response}")
    print_request_end("/debug")
    return response


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Upload mit ALLEN Debug Prints"""
    print_request_start("/upload", "POST")
    
    logger.info(f"🔵 Function: upload()")
    logger.debug(f"🔵 Parameter 'file' type: {type(file)}")
    logger.debug(f"🔵 file.filename: {file.filename}")
    logger.debug(f"🔵 file.content_type: {file.content_type}")
    
    # Read content
    logger.debug(f"🔵 Reading file content...")
    content = await file. read()
    logger.debug(f"🔵 Read {len(content)} bytes")
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_name = f"{timestamp}_{file.filename}"
    logger.debug(f"🔵 Generated unique filename: {unique_name}")
    
    # Build path
    filepath = UPLOAD_DIR / unique_name
    logger.debug(f"🔵 Full path: {filepath}")
    logger.debug(f"🔵 Absolute path: {filepath.absolute()}")
    
    # Save
    logger.debug(f"🔵 Writing to disk...")
    filepath.write_bytes(content)
    saved_size = filepath.stat().st_size
    logger.info(f"🔵 Saved!  File size: {saved_size} bytes")
    
    # Response
    response = {
        "filename": unique_name,
        "size": len(content),
        "path": str(filepath.absolute())
    }
    logger.debug(f"🔵 Response: {response}")
    
    print_request_end("/upload")
    return response


@app. post("/generate")
def generate(request: GenerateRequest):
    """Generate mit ALLEN Debug Prints"""
    print_request_start("/generate", "POST")
    
    logger.info(f"🔵 Function: generate()")
    logger.debug(f"🔵 Parameter 'request' type: {type(request)}")
    logger.debug(f"🔵 request object: {request}")
    logger.debug(f"🔵 request.filename: {request.filename}")
    logger.debug(f"🔵 request.target: {request.target}")
    logger.debug(f"🔵 request.name: {request.name}")
    
    # Pydantic model to dict
    logger.debug(f"🔵 Converting to dict...")
    data = request.model_dump()
    logger.debug(f"🔵 As dict: {data}")
    
    # Build model path
    logger.debug(f"🔵 Building model path...")
    logger.debug(f"   UPLOAD_DIR = {UPLOAD_DIR}")
    logger.debug(f"   request.filename = {request.filename}")
    
    model_path = UPLOAD_DIR / request.filename
    logger.debug(f"🔵 model_path = {model_path}")
    logger.debug(f"🔵 Checking if exists...")
    
    if not model_path.exists():
        logger.error(f"❌ File NOT found!")
        logger.error(f"   Available files:")
        for f in UPLOAD_DIR.glob('*'):
            logger.error(f"   - {f.name}")
        print_request_end("/generate")
        raise HTTPException(status_code=404, detail=f"Model not found:  {request.filename}")
    
    logger.info(f"✅ File found!")
    
    # Create job
    job_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.debug(f"🔵 Generated job_id: {job_id}")
    
    output_dir = OUTPUT_DIR / job_id
    logger.debug(f"🔵 output_dir:  {output_dir}")
    logger.debug(f"🔵 Creating directory...")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ Directory created!")
    
    # Simulate stedgeai (ohne wirklich auszuführen)
    logger.debug(f"🔵 Would run stedgeai here...")
    logger.debug(f"   Command: stedgeai generate -m {model_path} --target {request.target} -n {request.name} -o {output_dir}")
    
    # Create dummy files
    logger.debug(f"🔵 Creating dummy output files...")
    (output_dir / f"{request.name}.c").write_text("// Generated C code")
    (output_dir / f"{request.name}.h").write_text("// Generated header")
    logger.info(f"✅ Dummy files created!")
    
    # Response
    response = {
        "success": True,
        "job_id": job_id,
        "output_dir": str(output_dir)
    }
    logger.debug(f"🔵 Response: {response}")
    
    print_request_end("/generate")
    return response


@app.get("/outputs/{job_id}")
def list_outputs(job_id: str):
    """List files mit Debug"""
    print_request_start(f"/outputs/{job_id}", "GET")
    
    logger.info(f"🔵 Function: list_outputs()")
    logger.debug(f"🔵 Path parameter 'job_id': {job_id} (type: {type(job_id)})")
    
    # Build path
    output_dir = OUTPUT_DIR / job_id
    logger.debug(f"🔵 output_dir:  {output_dir}")
    logger.debug(f"🔵 Checking if exists...")
    
    if not output_dir.exists():
        logger.error(f"❌ Directory NOT found!")
        print_request_end(f"/outputs/{job_id}")
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    logger.info(f"✅ Directory found!")
    
    # List files
    logger.info(f"🔵 Listing files...")
    files = []
    for f in output_dir.iterdir():
        if f.is_file():
            file_info = {
                'name': f.name,
                'size': f.stat().st_size,
                'download_url': f'/download/{job_id}/{f.name}'
            }
            files. append(file_info)
            logger.info(f"   - {f.name} ({f.stat().st_size} bytes)")
    
    response = {
        'job_id': job_id,
        'files': files
    }
    logger.debug(f"🔵 Response: {response}")
    
    print_request_end(f"/outputs/{job_id}")
    return response


@app.get("/download/{job_id}/{filename}")
def download(job_id: str, filename:  str):
    """Download mit Debug"""
    print_request_start(f"/download/{job_id}/{filename}", "GET")
    
    logger.info(f"🔵 Function: download()")
    logger.debug(f"🔵 Path parameter 'job_id': {job_id}")
    logger.debug(f"🔵 Path parameter 'filename':  {filename}")
    
    # Build path
    filepath = OUTPUT_DIR / job_id / filename
    logger.debug(f"🔵 filepath: {filepath}")
    logger.debug(f"🔵 Checking if exists...")
    
    if not filepath. exists():
        logger.error(f"❌ File NOT found!")
        print_request_end(f"/download/{job_id}/{filename}")
        raise HTTPException(status_code=404, detail="File not found")
    
    logger.info(f"✅ File found!")
    logger.info(f"🔵 Sending file...")
    
    print_request_end(f"/download/{job_id}/{filename}")
    return FileResponse(filepath, filename=filename)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':

    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    log_level = logging.DEBUG if verbose else logging.INFO
    
    setup_logging(level=log_level)
    
    logger.info("Starting server...")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info"
    )
    