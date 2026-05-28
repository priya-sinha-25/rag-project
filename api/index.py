import sys
import os

# Add the src directory to the Python path so Vercel can find the nested code
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Import the FastAPI app instance
from mf_faq.ui.api import app
