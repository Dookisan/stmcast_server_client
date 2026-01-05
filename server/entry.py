import logging
import sys
import uvicorn
from utils.logging_config import setup_logging
from endpoints import app

# Configure logging
setup_logging(
    level=logging.INFO,
    log_file='logs/server.log',
    console=True
)

# Get logger for this module
logger = logging.getLogger(__name__)

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