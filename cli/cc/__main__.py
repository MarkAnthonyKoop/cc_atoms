"""Allow running cc as a module: python -m cc"""

import sys
from .main import main

if __name__ == "__main__":
    sys.exit(main())
