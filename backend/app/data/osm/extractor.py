"""
OpenStreetMap Data Extraction Module

Provides functionality to extract and process OpenStreetMap data
for buildings, roads, water bodies, and land use.

Usage:
    from app.data.osm.extractor import OSMExtractor
    
    extractor = OSMExtractor()
    buildings = extractor.extract_buildings(bbox)
"""

import os
import asyncio
import aiohttp
from typing import List, Optional, Dict, Any
import logging
import json

from app.config import settings

logger = logging.getLogger(__name__)


class OSMExtractor:
    """
    Extracts geospatial data from OpenStreetMap using Overpass API.
    """
    
    OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
    
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _bbox_to_overpass(self, bbox: List[float]) -> str:
        """Convert bbox [west, south, east, north] to Overpass format."""
        return f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}"
    
    async def _query_overpass(self, query: str) -> Dict[str, Any]:
        """Execute Overpass API query."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        
        async with self.session.post(
            self.OVERPASS_API_URL,
            data={"data": query},
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Overpass API error: {error_text}")
            
            return await response.json()
    
    async def extract_buildings(
        self,
        bbox: List[float],
        include_attributes: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract building footprints from OSM.
        
        Args:
            bbox: [west, south, east, north] bounding box
            include_attributes: Include OSM tags
        
        Returns:
            GeoJSON FeatureCollection of buildings
        """
        overpass_bbox = self._bbox_to_overpass(bbox)
        
        query = f"""
        [out:json][timeout:{self.timeout}];
        (
            way["building"]({overpass_bbox});
            relation["building"]({overpass_bbox});
        );
        out body;
        >;
        out skel qt;
        """
        
        result = await self._query_overpass(query)
        
        return self._osm_to_geojson(result, "building")
    
    async def extract_roads(
        self,
        bbox: List[float],
        road_types: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract road network from OSM.
        
        Args:
            bbox: Bounding box
            road_types: List of highway types (primary, secondary, residential, etc.)
        """
        overpass_bbox = self._bbox_to_overpass(bbox)
        
        if road_types is None:
            road_types = [
                "motorway", "trunk", "primary", "secondary",
                "tertiary", "residential", "service", "unclassified"
            ]
        
        road_filter = "|".join(road_types)
        
        query = f"""
        [out:json][timeout:{self.timeout}];
        (
            way["highway"~"^{road_filter}$"]({overpass_bbox});
        );
        out body;
        >;
        out skel qt;
        """
        
        result = await self._query_overpass(query)
        
        return self._osm_to_geojson(result, "highway")
    
    async def extract_water_bodies(
        self,
        bbox: List[float],
    ) -> Dict[str, Any]:
        """Extract water bodies from OSM."""
        overpass_bbox = self._bbox_to_overpass(bbox)
        
        query = f"""
        [out:json][timeout:{self.timeout}];
        (
            way["natural"="water"]({overpass_bbox});
            relation["natural"="water"]({overpass_bbox});
            way["waterway"]({overpass_bbox});
            relation["waterway"]({overpass_bbox});
        );
        out body;
        >;
        out skel qt;
        """
        
        result = await self._query_overpass(query)
        
        return self._osm_to_geojson(result, "water")
    
    async def extract_land_use(
        self,
        bbox: List[float],
    ) -> Dict[str, Any]:
        """Extract land use polygons from OSM."""
        overpass_bbox = self._bbox_to_overpass(bbox)
        
        query = f"""
        [out:json][timeout:{self.timeout}];
        (
            way["landuse"]({overpass_bbox});
            relation["landuse"]({overpass_bbox});
        );
        out body;
        >;
        out skel qt;
        """
        
        result = await self._query_overpass(query)
        
        return self._osm_to_geojson(result, "landuse")
    
    async def extract_all(
        self,
        bbox: List[float],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract all OSM features for an area.
        
        Returns:
            Dictionary with keys: buildings, roads, water, landuse
        """
        tasks = [
            self.extract_buildings(bbox),
            self.extract_roads(bbox),
            self.extract_water_bodies(bbox),
            self.extract_land_use(bbox),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "buildings": results[0] if not isinstance(results[0], Exception) else {"type": "FeatureCollection", "features": []},
            "roads": results[1] if not isinstance(results[1], Exception) else {"type": "FeatureCollection", "features": []},
            "water": results[2] if not isinstance(results[2], Exception) else {"type": "FeatureCollection", "features": []},
            "landuse": results[3] if not isinstance(results[3], Exception) else {"type": "FeatureCollection", "features": []},
        }
    
    def _osm_to_geojson(
        self,
        osm_data: Dict[str, Any],
        feature_type: str,
    ) -> Dict[str, Any]:
        """
        Convert OSM JSON response to GeoJSON.
        
        This is a simplified converter. For production use,
        consider using osmium or osm2geojson libraries.
        """
        features = []
        nodes = {}
        ways = {}
        
        for element in osm_data.get("elements", []):
            if element["type"] == "node":
                nodes[element["id"]] = {
                    "lat": element["lat"],
                    "lon": element["lon"],
                }
            elif element["type"] == "way":
                ways[element["id"]] = {
                    "nodes": element.get("nodes", []),
                    "tags": element.get("tags", {}),
                }
        
        for way_id, way_data in ways.items():
            coords = []
            for node_id in way_data["nodes"]:
                if node_id in nodes:
                    node = nodes[node_id]
                    coords.append([node["lon"], node["lat"]])
            
            if len(coords) >= 3:
                coords.append(coords[0])
                geometry = {
                    "type": "Polygon",
                    "coordinates": [coords],
                }
            elif len(coords) >= 2:
                geometry = {
                    "type": "LineString",
                    "coordinates": coords,
                }
            else:
                continue
            
            feature = {
                "type": "Feature",
                "id": f"way/{way_id}",
                "geometry": geometry,
                "properties": {
                    "feature_type": feature_type,
                    **way_data["tags"],
                },
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features,
        }


async def download_osm_for_area(
    bbox: List[float],
    output_dir: str = "data/osm",
) -> Dict[str, str]:
    """
    Download all OSM data for an area and save to files.
    
    Args:
        bbox: Bounding box
        output_dir: Output directory
    
    Returns:
        Dictionary mapping feature type to file path
    """
    os.makedirs(output_dir, exist_ok=True)
    
    async with OSMExtractor() as extractor:
        data = await extractor.extract_all(bbox)
    
    file_paths = {}
    
    for feature_type, geojson in data.items():
        file_path = os.path.join(output_dir, f"{feature_type}.geojson")
        with open(file_path, "w") as f:
            json.dump(geojson, f)
        file_paths[feature_type] = file_path
        logger.info(f"Saved {len(geojson['features'])} {feature_type} features to {file_path}")
    
    return file_paths


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract OSM data")
    parser.add_argument("--bbox", required=True, help="Bounding box: west,south,east,north")
    parser.add_argument("--output", default="data/osm", help="Output directory")
    
    args = parser.parse_args()
    
    bbox = [float(x) for x in args.bbox.split(",")]
    
    asyncio.run(download_osm_for_area(bbox, args.output))
