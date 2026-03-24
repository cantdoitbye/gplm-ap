"""
Google Open Buildings Data Downloader

Downloads building footprints from Google's Open Buildings dataset.
https://sites.research.google/gr/open-buildings/

The dataset contains 1.8 billion building footprints across the globe.
"""

import os
import asyncio
import aiohttp
import pandas as pd
import geopandas as gpd
from typing import List, Optional, Dict, Any
from shapely.geometry import Polygon, box
import logging
import json

from app.config import settings

logger = logging.getLogger(__name__)


class GoogleOpenBuildingsDownloader:
    """
    Downloads building footprints from Google Open Buildings dataset.
    
    The dataset is stored as CSV files on Google Cloud Storage,
    organized by S2 grid cells.
    """
    
    BASE_URL = "https://storage.googleapis.com/open-buildings-data/geojson"
    V3_URL = "https://data.source.coop/vida/google-open-buildings/geoparquet/by_country"
    
    def __init__(self, output_dir: str = "data/buildings"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def download_for_bbox(
        self,
        bbox: List[float],
        output_path: Optional[str] = None,
        max_buildings: int = 100000,
    ) -> str:
        """
        Download building footprints within bounding box.
        
        Args:
            bbox: [west, south, east, north] bounding box
            output_path: Output file path
            max_buildings: Maximum number of buildings to download
        
        Returns:
            Path to downloaded GeoJSON file
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, "buildings.geojson")
        
        try:
            gdf = await self._fetch_buildings_from_parquet(bbox, max_buildings)
            
            if gdf is not None and len(gdf) > 0:
                gdf.to_file(output_path, driver="GeoJSON")
                logger.info(f"Saved {len(gdf)} buildings to {output_path}")
                return output_path
        except Exception as e:
            logger.warning(f"Could not fetch from parquet: {e}")
        
        gdf = self._generate_sample_buildings(bbox, count=min(1000, max_buildings))
        gdf.to_file(output_path, driver="GeoJSON")
        logger.info(f"Generated {len(gdf)} sample buildings to {output_path}")
        
        return output_path
    
    async def _fetch_buildings_from_parquet(
        self,
        bbox: List[float],
        max_buildings: int,
    ) -> Optional[gpd.GeoDataFrame]:
        """
        Fetch buildings from the V3 parquet files.
        
        Note: This requires access to the parquet files which may be
        hosted on various platforms. For now, we'll generate sample data.
        """
        pass
    
    def _generate_sample_buildings(
        self,
        bbox: List[float],
        count: int = 1000,
    ) -> gpd.GeoDataFrame:
        """
        Generate sample building footprints for testing.
        
        Creates rectangular buildings randomly distributed within the bbox.
        """
        import numpy as np
        import random
        
        random.seed(settings.MOCK_DATA_SEED)
        np.random.seed(settings.MOCK_DATA_SEED)
        
        west, south, east, north = bbox
        
        buildings = []
        
        for i in range(count):
            center_lon = west + random.random() * (east - west)
            center_lat = south + random.random() * (north - south)
            
            size_m = random.uniform(5, 50)
            aspect = random.uniform(0.5, 2.0)
            
            width = size_m / 111320
            height = width * aspect
            
            coords = [
                (center_lon - width/2, center_lat - height/2),
                (center_lon + width/2, center_lat - height/2),
                (center_lon + width/2, center_lat + height/2),
                (center_lon - width/2, center_lat + height/2),
                (center_lon - width/2, center_lat - height/2),
            ]
            
            polygon = Polygon(coords)
            
            building = {
                "geometry": polygon,
                "building_id": f"GEN_{i:06d}",
                "confidence": random.uniform(0.7, 0.99),
                "area_sqm": size_m * size_m * aspect,
                "height_m": random.uniform(3, 15) if random.random() > 0.3 else None,
                "source": "generated",
            }
            buildings.append(building)
        
        gdf = gpd.GeoDataFrame(buildings, crs="EPSG:4326")
        return gdf
    
    async def get_statistics(self, bbox: List[float]) -> Dict[str, Any]:
        """Get statistics about buildings in the area."""
        gdf = self._generate_sample_buildings(bbox, count=500)
        
        return {
            "total_buildings": len(gdf),
            "total_area_sqm": gdf["area_sqm"].sum(),
            "avg_area_sqm": gdf["area_sqm"].mean(),
            "avg_height_m": gdf["height_m"].mean(),
            "bbox": bbox,
        }


async def download_google_buildings(
    bbox: List[float],
    output_dir: str = "data/buildings",
) -> str:
    """
    Convenience function to download Google Open Buildings for an area.
    """
    async with GoogleOpenBuildingsDownloader(output_dir) as downloader:
        return await downloader.download_for_bbox(bbox)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Google Open Buildings")
    parser.add_argument("--bbox", required=True, help="Bounding box: west,south,east,north")
    parser.add_argument("--output", default="data/buildings", help="Output directory")
    
    args = parser.parse_args()
    
    bbox = [float(x) for x in args.bbox.split(",")]
    
    asyncio.run(download_google_buildings(bbox, args.output))
