import logging
from utils.logging_config import setup_logging
from discovery import discover_server, heartbeat
from utils.test_suite import TestSuite
import sys

# Configure logging
setup_logging(
    level=logging.INFO,
    log_file='logs/server.log',
    console=True
)

# Get logger for this module
logger = logging.getLogger(__name__)


class Client(object):

    def __init__(self):
        self.Server_URL = discover_server()
        heartbeat(self.Server_URL)
    #client methods


# testfunction for development
def main():
    CLIENT = Client()
    Tests = TestSuite(CLIENT.Server_URL)
    if input("Press 1 to start tests...") == "1":
        Tests.server_test()
        pass


    
if __name__ == '__main__': 
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    log_level = logging.DEBUG if verbose else logging.INFO
    
    setup_logging(level=log_level)
    main()