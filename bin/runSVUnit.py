#!/usr/bin/env python3

import sys
import os

# Add the bin directory to sys.path to allow importing svunit package
# when running directly from the source tree without installation.
bin_dir = os.path.dirname(os.path.abspath(__file__))
if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

from svunit.main import main

if __name__ == "__main__":
    sys.exit(main())
