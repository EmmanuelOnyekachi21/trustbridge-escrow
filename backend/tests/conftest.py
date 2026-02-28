"""
Pytest configuration for test suite.
"""
import sys
from pathlib import Path

# Add parent directory (backend) to Python path so 'app' module can be imported
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
