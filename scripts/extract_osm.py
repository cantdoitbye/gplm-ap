"""
Extract OSM Data for Area of Interest

Downloads buildings, roads, water bodies, and land use from OpenStreetMap.

Usage:
    python scripts/extract_osm.py --bbox 80.5,16.4,80.8,16.6
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.data.osm.extractor import OSMExtractor, download_osm_for_area


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract OSM data")
    parser.add_argument(
        "--bbox",
        help="Bounding box: west,south,east,north",
    )
    parser.add_argument(
        "--output",
        default="data/osm",
        help="Output directory",
    )
    
    args = parser.parse_args()
    
    if args.bbox:
        bbox = [float(x) for x in args.bbox.split(",")]
    else:
        center_lat = settings.AOI_CENTER_LAT
        center_lon = settings.AOI_CENTER_LON
        buffer = settings.AOI_BUFFER_KM / 111.0
        
        bbox = [
            center_lon - buffer,
            center_lat - buffer,
            center_lon + buffer,
            center_lat + buffer,
        ]
    
    print(f"Extracting OSM data for bbox: {bbox}")
    
    paths = await download_osm_for_area(bbox, args.output)
    
    print(f"\nExtracted files:")
    for key, path in paths.items():
        print(f"  {key}: {path}")


if __name__ == "__main__":
    asyncio.run(main())
