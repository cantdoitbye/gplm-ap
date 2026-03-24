"""
Download Sentinel-2 Satellite Imagery

This script downloads Sentinel-2 imagery from Copernicus Data Space
for the configured Area of Interest (AOI).

Usage:
    python scripts/download_sentinel.py --start 2024-01-01 --end 2024-03-31
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.data.satellite.sentinel import Sentinel2Downloader, download_sentinel2_for_area


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Sentinel-2 imagery")
    parser.add_argument(
        "--start",
        default="2024-01-01",
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        default="2024-03-31",
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        default="data/satellite",
        help="Output directory",
    )
    parser.add_argument(
        "--cloud",
        type=float,
        default=30.0,
        help="Maximum cloud cover percentage",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of scenes to download",
    )
    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Only search, don't download",
    )
    
    args = parser.parse_args()
    
    center_lat = settings.AOI_CENTER_LAT
    center_lon = settings.AOI_CENTER_LON
    buffer = settings.AOI_BUFFER_KM / 111.0
    
    bbox = [
        center_lon - buffer,
        center_lat - buffer,
        center_lon + buffer,
        center_lat + buffer,
    ]
    
    print(f"Area of Interest: {bbox}")
    print(f"Date Range: {args.start} to {args.end}")
    print(f"Max Cloud Cover: {args.cloud}%")
    
    if args.search_only:
        async with Sentinel2Downloader() as downloader:
            scenes = await downloader.search(
                bbox=bbox,
                start_date=args.start,
                end_date=args.end,
                cloud_cover_max=args.cloud,
                limit=args.limit,
            )
            
            print(f"\nFound {len(scenes)} scenes:")
            for scene in scenes:
                print(f"  - {scene.title}")
                print(f"    Date: {scene.acquisition_date}")
                print(f"    Cloud: {scene.cloud_cover:.1f}%")
                print(f"    Size: {scene.size_mb:.1f} MB")
    else:
        paths = await download_sentinel2_for_area(
            bbox=bbox,
            start_date=args.start,
            end_date=args.end,
            output_dir=args.output,
            cloud_cover_max=args.cloud,
            limit=args.limit,
        )
        
        print(f"\nDownloaded {len(paths)} scenes:")
        for path in paths:
            print(f"  - {path}")


if __name__ == "__main__":
    asyncio.run(main())
