# conftest.py for WranglesPY tests
# Ensures the package root is on sys.path for test discovery and imports
import sys
import os

# Add the project root to sys.path if not already present
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
