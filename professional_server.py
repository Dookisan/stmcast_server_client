#!/usr/bin/env python3
"""
Professional Server with proper logging
"""

import json
import socket
import threading
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import uvicorn

# ============================================================================
# LOGGING SETUP
# ============================================================================

# Create logger
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
# Network Discovery
# ============================================================================

def get_local_ip():
    """Get local IP address"""
    try: 
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        logger.debug(f"Local IP detected: {ip}")
        return ip
    except Exception as e:
        logger.error(f"Failed to get local IP: {e}")
        return "127.0.0.1"

def broadcast_loop():
    """Send discovery broadcasts"""
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket. SOL_SOCKET, socket. SO_BROADCAST, 1)
        
        local_ip = get_local_ip()
        logger.info(f"Broadcast loop started on IP {local_ip}, port 5001")
        
        while True:
            try: 
                message = json.dumps({
                    'service': 'stedgeai-api',
                    'ip': local_ip,
                    'port': 5000,
                    'timestamp': datetime.now().isoformat()
                }).encode()
                
                sock.sendto(message, ('<broadcast>', 5001))
                logger.debug("Broadcast sent")
                
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                time.sleep(5)
                
    except Exception as e:
        logger.critical(f"Failed to start broadcast loop: {e}")

# ============================================================================
# LIFESPAN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    
    # Startup
    logger.info("="*60)
    logger.info("SERVER STARTING")
    logger.info("="*60)
    logger.info(f"Upload folder: {UPLOAD_DIR. absolute()}")
    logger.info(f"Output folder: {OUTPUT_DIR.absolute()}")
    logger.info(f"Local IP: {get_local_ip()}")
    logger.info(f"API Docs: http://localhost:5000/docs")
    logger.info("="*60)
    
    # Start broadcast thread
    logger.info("Starting discovery broadcast thread...")
    broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
    broadcast_thread.start()
    logger.info("Discovery broadcast started")
    
    yield
    
    # Shutdown
    logger.info("="*60)
    logger.info("SERVER SHUTTING DOWN")
    logger.info("="*60)

# ============================================================================
# APP
# ============================================================================

app = FastAPI(
    title="STEdgeAI API",
    description="Professional API for STEdgeAI code generation",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """Root endpoint"""
    logger.debug("Root endpoint accessed")
    return {
        "message": "STEdgeAI API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/debug")
def debug():
    """Debug endpoint - shows uploaded files and outputs"""
    logger.debug("Debug endpoint accessed")
    
    uploads = list(UPLOAD_DIR. glob('*'))
    outputs = list(OUTPUT_DIR.glob('*'))
    
    logger.debug(f"Found {len(uploads)} uploads, {len(outputs)} outputs")
    
    return {
        "uploads": [f.name for f in uploads],
        "outputs": [f.name for f in outputs]
    }


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """Upload a model file"""
    logger.info(f"Upload request received: {file.filename}")
    
    try:
        # Read content
        content = await file.read()
        logger.debug(f"Read {len(content)} bytes")
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_name = f"{timestamp}_{file.filename}"
        filepath = UPLOAD_DIR / unique_name
        
        # Save
        filepath.write_bytes(content)
        logger.info(f"File saved: {unique_name} ({len(content)} bytes)")
        
        return {
            "success": True,
            "filename": unique_name,
            "size": len(content),
            "path": str(filepath. absolute())
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/generate")
def generate(request: GenerateRequest):
    """Generate C code from model"""
    logger. info(f"Generate request:  {request.filename} -> {request.name} ({request.target})")
    
    try:
        # Check if model exists
        model_path = UPLOAD_DIR / request.filename
        
        if not model_path.exists():
            logger.warning(f"Model not found: {request. filename}")
            available = [f.name for f in UPLOAD_DIR.glob('*')]
            logger.debug(f"Available files: {available}")
            raise HTTPException(
                status_code=404,
                detail=f"Model not found: {request. filename}"
            )
        
        logger.debug(f"Model found: {model_path}")
        
        # Create job
        job_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = OUTPUT_DIR / job_id
        output_dir. mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Created output directory: {output_dir}")
        
        # TODO: Run stedgeai here
        logger.info(f"Would run:  stedgeai generate -m {model_path} --target {request.target} -n {request.name}")
        
        # Create dummy files
        (output_dir / f"{request.name}.c").write_text("// Generated C code")
        (output_dir / f"{request.name}.h").write_text("// Generated header")
        
        logger.info(f"Code generation completed:  job_id={job_id}")
        
        return {
            "success": True,
            "job_id": job_id,
            "output_dir": str(output_dir)
        }
        
    except HTTPException: 
        raise
    except Exception as e:
        logger.error(f"Generate failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.get("/outputs/{job_id}")
def list_outputs(job_id: str):
    """List generated files for a job"""
    logger.debug(f"List outputs request:  job_id={job_id}")
    
    output_dir = OUTPUT_DIR / job_id
    
    if not output_dir.exists():
        logger.warning(f"Job not found: {job_id}")
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    files = []
    for f in output_dir.iterdir():
        if f.is_file():
            files.append({
                'name': f.name,
                'size': f.stat().st_size,
                'download_url': f'/download/{job_id}/{f.name}'
            })
    
    logger.info(f"Listed {len(files)} files for job {job_id}")
    
    return {
        'job_id': job_id,
        'files': files
    }


@app.get("/download/{job_id}/{filename}")
def download(job_id: str, filename:  str):
    """Download a generated file"""
    logger.info(f"Download request: job_id={job_id}, file={filename}")
    
    filepath = OUTPUT_DIR / job_id / filename
    
    if not filepath.exists():
        logger.warning(f"File not found:  {filepath}")
        raise HTTPException(status_code=404, detail="File not found")
    
    logger.debug(f"Sending file: {filepath}")
    return FileResponse(filepath, filename=filename)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Setup logging
    import sys
    
    # Check for verbose flag
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    log_level = logging.DEBUG if verbose else logging.INFO
    
    setup_logging(level=log_level)
    
    logger.info("Starting server...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="warning"  # Suppress uvicorn's own logs
    )