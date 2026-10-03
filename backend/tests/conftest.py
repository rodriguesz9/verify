"""Same offline tests can run with pytest or unittest discovery."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import helpers  # isolates provider configuration before application imports
