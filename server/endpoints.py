from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import logging
from pathlib import Path
import threading
from datetime import datetime
from config import UPLOAD_DIR, OUTPUT_DIR, GenerateRequest
from discovery import discovery_server, get_local_ip
from utils.format import print_request_start, print_request_end
from utils.finder import FilesystemFinder
from utils.stedgeai import STEdgeAI

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager
    Code BEFORE yield = startup
    Code AFTER yield = shutdown
    """

    # ===== STARTUP =====
    print(f"{80*'='}\n")
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
    
    # START STEDGEAI FINDER THREAD
    logger.info("🔎 Starting stedgeai finder thread...")
    STEDGEAI_FINDER = FilesystemFinder

    finder = FilesystemFinder(
        "stedgeai.exe",
        validator=lambda p:  p.stat().st_size > 100_000
    )
    path = finder.find()

    finder_thread = threading.Thread(target=finder.find, daemon=True)
    finder_thread.start()
    yield  
    
    # ===== SHUTDOWN =====
    
    print("🛑 SERVER SHUTTING DOWN")
    

app = FastAPI(
    title="Debug Server",
    lifespan=lifespan  
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
    content = await file.read()
    logger.debug(f"🔵 Read {len(content)} bytes")
    
    # Generate filename
    
    logger.debug(f"🔵 Generated unique filename: {file.filename}")
    
    # Build path
    filepath = UPLOAD_DIR / file.filename
    logger.debug(f"🔵 Full path: {filepath}")
    logger.debug(f"🔵 Absolute path: {filepath.absolute()}")
    
    # Save
    logger.debug(f"🔵 Writing to disk...")
    filepath.write_bytes(content)
    saved_size = filepath.stat().st_size
    logger.info(f"🔵 Saved!  File size: {saved_size} bytes")
    
    # Response
    response = {
        "filename": file.filename,
        "size": len(content),
        "path": str(filepath.absolute())
    }
    logger.debug(f"🔵 Response: {response}")
    
    print_request_end("/upload")
    return response


@app.post("/generate")
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
    
    prefix = "err_seq_"
    logger.debug(f"🔵 Extracting number from filename: {request.filename}")
    nn_number = ''.join(filter(str.isdigit, request.filename))
    logger.debug(f"🔵 Extracted number: '{nn_number}'")
    nn_name = f"{prefix}{nn_number}"

    # Create job
    job_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.debug(f"🔵 Generated job_id: {job_id}")
    
    output_dir = OUTPUT_DIR / nn_name
    logger.debug(f"🔵 output_dir:  {output_dir}")
    logger.debug(f"🔵 Creating directory...")
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"✅ Directory created!")
    
    # Simulate stedgeai (ohne wirklich auszuführen)
    logger.debug(f"🔵 Initialise stedgeai ...")

    if not nn_number:
        logger.warning(f"⚠️ No number found in filename '{request.filename}', using default '0'")
        nn_number = "0"
    
    
    logger.debug(f"🔵 Generated network name: {nn_name}")
    
    stedgeai = STEdgeAI(model_file=model_path, network=nn_name, output_dir=output_dir)
    
    # Run stedgeai generate
    logger.debug(f"🔵 Running stedgeai generate...")
    logger.debug(f"🔵 Output will be saved to: {output_dir}")
    success = stedgeai.generate_model()
    
    if not success:
        logger.error(f"❌ stedgeai generation failed!")
        print_request_end("/generate")
        raise HTTPException(status_code=500, detail="Model generation failed")
    
    logger.info(f"✅ stedgeai generation completed!")
    logger.info(f"✅ Files saved to {output_dir}")
    
    # Response
    response = {
        "success": True,
        "name": nn_name,
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