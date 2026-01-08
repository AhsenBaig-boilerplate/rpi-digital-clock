#!/usr/bin/env python3
"""
Print build information embedded in the app image.
"""

import json
import sys
from pathlib import Path

from utils import load_build_info, format_build_info, setup_logging


def main():
    setup_logging("INFO")
    info = load_build_info()
    print("=== Build Info (concise) ===")
    print(format_build_info(info))
    print("\n=== Build Info (raw JSON) ===")
    if info is None:
        print("{}")
        sys.exit(1)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
