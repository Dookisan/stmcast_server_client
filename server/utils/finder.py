import json
import logging
from pathlib import Path
from typing import Optional, Callable


logger = logging.getLogger(__name__)

class FilesystemFinder(object):
    """Generic file/folder finder utility
    Prerequisit to allocate stedgeai.exe path and 
    the STMCast project folder. It allocates the paths
    for the precompiled NN models in the project folder.

    Usage:
        # Find file:
        finder = FilesystemFinder("stedgeai.exe")
        path = finder.find()
        
        # Find directory: 
        finder = FilesystemFinder("STM32CubeAI", is_dir=True)
        path = finder.find()
        
        # With validator:
        finder = FilesystemFinder(
            "stedgeai.exe",
            validator=lambda p: p.stat().st_size > 100_000
        )
    """

    def __init__(
        self,
        target:  str,
        is_dir:  bool = False,
        validator:  Optional[Callable[[Path], bool]] = None,
        config_file: Optional[Path] = None
    ):
        """
        Initialize finder
        
        Args:
            target: Name of file or directory to find
            is_dir: True if searching for directory, False for file
            validator: Optional validation function
            config_file: Optional config file path for caching
        """
        self.target = target
        self.is_dir = is_dir
        self.validator = validator
        
        # Config for caching
        if config_file:
            self.config_file = config_file
        else:
            safe_name = target.replace(".", "_").replace("/", "_")
            self.config_file = Path(f"config/{safe_name}.json")
        
        self.cached_path:  Optional[Path] = None
    
    
    def find(self, use_cache: bool = True) -> Optional[Path]:
        """
        Find target on filesystem
        
        Args: 
            use_cache: If True, use cached result if available
            
        Returns: 
            Path if found, None otherwise
        """
        
        logger.info(f"Searching for:  {self.target}")
        
        # 1. Check memory cache
        if self.cached_path:
            return self.cached_path
        
        # 2. Check saved config
        if use_cache: 
            saved = self._load_cache()
            if saved:
                self.cached_path = saved
                return saved
        
        # 3. Search all drives
        logger.info("Searching filesystem...  (this may take 10-30 seconds)")
        
        for drive in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            root = Path(f"{drive}:/")
            if not root.exists():
                continue
            
            logger.info(f"Searching {drive}:/...")
            
            try:
                # Search recursively
                for item in root.rglob(self.target):
                    if self._is_valid(item):
                        logger.info(f"✅ Found: {item}")
                        self._save_cache(item)
                        self.cached_path = item
                        return item
            except Exception as e:
                logger.debug(f"Error on {drive}::  {e}")
        
        logger.error(f"❌ {self.target} not found")
        return None
    
    
    def get(self) -> Path:
        """
        Get path (raises error if not found)
        
        Returns:
            Path to target
            
        Raises:
            FileNotFoundError: If not found
        """
        path = self.cached_path or self.find()
        if not path:
            raise FileNotFoundError(f"{self.target} not found")
        return path
    
    
    def reset(self):
        """Clear cache"""
        self.cached_path = None
        if self.config_file.exists():
            self. config_file.unlink()
    
    
    def _is_valid(self, path: Path) -> bool:
        """Check if path is valid match"""
        
        if not path.exists():
            return False
        
        # === SKIP RECYCLE BIN & OTHER SYSTEM FOLDERS ===
        path_str = str(path).lower()
        
        skip_patterns = [
            '$recycle.bin',    # Recycle Bin
            'recycler',        # Old recycle bin
            ':\\$recycle',     # Alternative
            'system volume information',  # System
            'windows\\winsxs',  # Windows component store
            'appdata\\local\\temp',  # Temp files
            '__pycache__',     # Python cache
            '.git',            # Git repos
            'node_modules',    # NPM
        ]
        
        if any(skip in path_str for skip in skip_patterns):
            logger.debug(f"Skipping system/trash folder: {path}")
            return False
    
        if self.is_dir and not path.is_dir():
            return False
        
        if not self.is_dir and not path.is_file():
            return False
        
        if self.validator and not self.validator(path):
            return False
        
        return True
    
    
    def _load_cache(self) -> Optional[Path]:
        """Load cached path"""
        if not self.config_file.exists():
            return None
        
        try:
            data = json.loads(self.config_file.read_text())
            path = Path(data['path'])
            
            if self._is_valid(path):
                logger.info(f"Using cached:  {path}")
                return path
        except Exception as e:
            logger.debug(f"Cache load failed: {e}")
        
        return None
    
    
    def _save_cache(self, path: Path):
        """Save path to cache"""
        try: 
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self.config_file.write_text(json.dumps({'path': str(path)}, indent=2))
        except Exception as e:
            logger. debug(f"Cache save failed:  {e}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def find_file(name: str, validator: Optional[Callable] = None) -> Optional[Path]:
    """Find a file"""
    return FilesystemFinder(name, is_dir=False, validator=validator).find()


def find_dir(name: str, validator: Optional[Callable] = None) -> Optional[Path]:
    """Find a directory"""
    return FilesystemFinder(name, is_dir=True, validator=validator).find()

# ============================================================================
# TEST
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Example:  Find stedgeai.exe
    finder = FilesystemFinder(
        "stedgeai.exe",
        validator=lambda p:  p.stat().st_size > 100_000
    )
    path = finder.find()

    if path:
        print(f"✅ Found: {path}")
    else:
        print("❌ Not found")

    finder2 = FilesystemFinder("workspace_1.16.1", is_dir=True)
    path2 = finder2.find()

    if path2:
        print(f"✅ Found: {path2}")
    else:
        print("❌ Not found")