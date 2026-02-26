#!/usr/bin/env python3
"""
Template script for execution layer.

This is a deterministic, testable script that performs a specific task.
Copy this file and rename it to match your directive.

Usage:
    python execution/script_name.py --arg1 value1 --arg2 value2

Requirements:
    pip install -r requirements.txt
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Description of what this script does")
    parser.add_argument(
        "--input", type=str, required=True, help="Path to input file or data"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to output file (default: auto-generated in .tmp/)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


def main(input_path: str, output_path: str = None) -> dict:
    """
    Main execution function.

    Args:
        input_path: Path to input file or data source
        output_path: Optional path for output file

    Returns:
        Dictionary containing results and metadata

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If input data is invalid
    """
    # Set default output path
    if output_path is None:
        output_path = PROJECT_ROOT / ".tmp" / "output"
    else:
        output_path = Path(output_path)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Processing input: {input_path}")
    logger.info(f"Output will be saved to: {output_path}")

    # Validate input
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # TODO: Implement your processing logic here
    result = {
        "status": "success",
        "input": str(input_path),
        "output": str(output_path),
        "data": None,  # Your processed data here
    }

    # Save output
    # with open(output_path, 'w') as f:
    #     json.dump(result, f, indent=2)

    logger.info(f"Processing complete: {result['status']}")
    return result


if __name__ == "__main__":
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        result = main(input_path=args.input, output_path=args.output)
        print(f"Done: {result['status']}")
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        sys.exit(1)
