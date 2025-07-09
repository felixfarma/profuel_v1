# conftest.py
import os
import sys

# Inserta la carpeta raíz del proyecto en sys.path
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
