from typing import TypedDict, Optional, Literal
from pathlib import Path
from dataclasses import dataclass, field
import subprocess
import json
import logging
from config import CONFIG_DIR

logger = logging.getLogger(__name__)

"""Contains the STEdgeAI options for easy server integration"""
class STEdgeAI:
    def __init__(self, model_file: Optional[Path], network: str, output_dir: Optional[Path] = None):
        
        self.stedgeai_path = self.set_stedgeai_path()
        self.model_file = model_file
        self.stm_cast_workspace = self.set_workspace_path()
        self.network_name = network
        self.output_dir = output_dir

    def generate_model(self) -> bool:
        
        logger.debug(f"🔧 stedgeai_path: {self.stedgeai_path}")
        logger.debug(f"🔧 model_file: {self.model_file}")
        logger.debug(f"🔧 output_dir: {self.output_dir}")

        cmd = [
            self.stedgeai_path,
            "generate",
            "-m", str(self.model_file),
            "-n", self.network_name,
            "--target", "stm32f4"
        ]
        
        # Add output directory if specified
        if self.output_dir:
            cmd.extend(["--output", str(self.output_dir)])
        
        logger.debug(f"🔧 Command: {' '.join(cmd)}")
    
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            logger.debug(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            logger.error(f"STDERR:\n{result.stderr}")
    
        return result.returncode == 0

    def set_stedgeai_path(self) -> str:
        #get stedgeapi path
        with open(CONFIG_DIR/"stedgeai_exe.json","r") as f:
            config = json.load(f)
            stedgeai_path = config.get("path", "").strip()
        
        # Validate path exists
        if not Path(stedgeai_path).exists():
            logger.error(f"❌ stedgeai.exe not found at: {stedgeai_path}")
            raise FileNotFoundError(f"stedgeai.exe not found at: {stedgeai_path}")
        
        logger.debug(f"✅ Found stedgeai.exe at: {stedgeai_path}")
        return stedgeai_path

    def set_workspace_path(self) -> str:
        with open(CONFIG_DIR/"workspace_1_16_1.json","r") as f:
            config = json.load(f)
            workspace_path = config.get("path", "").strip()

        return workspace_path