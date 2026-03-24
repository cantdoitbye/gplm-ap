"""
Generate Mock Data for Development

This script generates synthetic property records, municipalities,
and change history for development and testing.

Usage:
    python scripts/generate_mock_data.py --properties 1000 --municipalities 3
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.data.mock.generator import MockDataGenerator


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate mock data for AIKOSH-5")
    parser.add_argument(
        "--output",
        default="data/mock",
        help="Output directory",
    )
    parser.add_argument(
        "--properties",
        type=int,
        default=1000,
        help="Number of properties to generate",
    )
    parser.add_argument(
        "--municipalities",
        type=int,
        default=3,
        help="Number of municipalities",
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=settings.AOI_CENTER_LAT,
        help="Center latitude",
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=settings.AOI_CENTER_LON,
        help="Center longitude",
    )
    
    args = parser.parse_args()
    
    print(f"Generating mock data...")
    print(f"  Center: ({args.lat}, {args.lon})")
    print(f"  Municipalities: {args.municipalities}")
    print(f"  Properties per municipality: {args.properties // args.municipalities}")
    print(f"  Output: {args.output}")
    print()
    
    generator = MockDataGenerator(output_dir=args.output)
    
    result = generator.generate_all(
        center_lat=args.lat,
        center_lon=args.lon,
        municipalities_count=args.municipalities,
        properties_per_municipality=args.properties // args.municipalities,
    )
    
    print("Generated data:")
    print(json.dumps(result["summary"], indent=2))
    print()
    print("Files created:")
    for key, path in result["file_paths"].items():
        print(f"  {key}: {path}")


if __name__ == "__main__":
    main()
