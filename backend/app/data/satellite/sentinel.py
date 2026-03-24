"""
Copernicus Data Space Sentinel-2 Download Script

This module provides functionality to download Sentinel-2 satellite imagery
from the Copernicus Data Space (https://dataspace.copernicus.eu/).

Usage:
    from app.data.satellite.sentinel import Sentinel2Downloader
    
    downloader = Sentinel2Downloader(username, password)
    downloader.download(bbox, start_date, end_date)
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SentinelScene:
    """Represents a Sentinel-2 scene."""
    scene_id: str
    title: str
    acquisition_date: datetime
    cloud_cover: float
    footprint: Dict[str, Any]
    download_url: str
    quicklook_url: str
    tile_id: str
    product_type: str
    processing_level: str
    size_mb: float


class Sentinel2Downloader:
    """
    Downloads Sentinel-2 imagery from Copernicus Data Space.
    
    Uses the OData API to search and download products.
    API Documentation: https://documentation.dataspace.copernicus.eu/APIs/OpenSearch.html
    """
    
    AUTH_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    SEARCH_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products"
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.username = username or settings.COPERNICUS_USERNAME
        self.password = password or settings.COPERNICUS_PASSWORD
        self.access_token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def authenticate(self) -> str:
        """
        Authenticate with Copernicus Data Space and get access token.
        """
        if not self.username or not self.password:
            raise ValueError("Copernicus credentials not configured. Set COPERNICUS_USERNAME and COPERNICUS_PASSWORD.")
        
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "client_id": "cdse-public",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.AUTH_URL, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Authentication failed: {error_text}")
                
                result = await response.json()
                self.access_token = result["access_token"]
                logger.info("Successfully authenticated with Copernicus Data Space")
                return self.access_token
    
    def build_search_query(
        self,
        bbox: List[float],
        start_date: datetime,
        end_date: datetime,
        cloud_cover_max: float = 30.0,
        product_type: str = "S2MSI2A",
    ) -> str:
        """
        Build OData search query for Sentinel-2 products.
        
        Args:
            bbox: [west, south, east, north] bounding box coordinates
            start_date: Start date for search
            end_date: End date for search
            cloud_cover_max: Maximum cloud cover percentage
            product_type: Sentinel-2 product type (S2MSI2A, S2MSI1C)
        """
        west, south, east, north = bbox
        aoi_wkt = f"POLYGON(({west} {south},{east} {south},{east} {north},{west} {north},{west} {south}))"
        
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        query = (
            f"Collection/Name eq 'SENTINEL-2' "
            f"and OData.CSC.Intersects(area=geography'SRID=4326;{aoi_wkt}') "
            f"and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{product_type}') "
            f"and ContentDate/Start gt {start_str} "
            f"and ContentDate/Start lt {end_str} "
            f"and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {cloud_cover_max})"
        )
        
        return query
    
    async def search(
        self,
        bbox: List[float],
        start_date: datetime,
        end_date: datetime,
        cloud_cover_max: float = 30.0,
        product_type: str = "S2MSI2A",
        limit: int = 10,
    ) -> List[SentinelScene]:
        """
        Search for Sentinel-2 scenes matching criteria.
        
        Args:
            bbox: [west, south, east, north] bounding box
            start_date: Start date for search
            end_date: End date for search
            cloud_cover_max: Maximum cloud cover percentage
            product_type: Sentinel-2 product type
            limit: Maximum number of results
        
        Returns:
            List of SentinelScene objects
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        if not self.access_token:
            await self.authenticate()
        
        query = self.build_search_query(bbox, start_date, end_date, cloud_cover_max, product_type)
        
        params = {
            "$filter": query,
            "$orderby": "ContentDate/Start desc",
            "$top": limit,
            "$expand": "Attributes",
        }
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        scenes = []
        
        async with self.session.get(self.SEARCH_URL, params=params, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Search failed: {error_text}")
            
            result = await response.json()
            
            for item in result.get("value", []):
                scene = self._parse_scene(item)
                scenes.append(scene)
        
        logger.info(f"Found {len(scenes)} Sentinel-2 scenes")
        return scenes
    
    def _parse_scene(self, item: Dict[str, Any]) -> SentinelScene:
        """Parse API response into SentinelScene object."""
        attributes = {attr["Name"]: attr.get("Value") for attr in item.get("Attributes", [])}
        
        footprint = item.get("GeoFootprint", {})
        
        return SentinelScene(
            scene_id=item.get("Id", ""),
            title=item.get("Name", ""),
            acquisition_date=datetime.fromisoformat(item.get("ContentDate", {}).get("Start", "").replace("Z", "+00:00")),
            cloud_cover=float(attributes.get("cloudCover", 100)),
            footprint=footprint,
            download_url=f"{self.DOWNLOAD_URL}({item.get('Id')})/$value",
            quicklook_url=item.get("Quicklook", ""),
            tile_id=attributes.get("tileId", ""),
            product_type=attributes.get("productType", ""),
            processing_level=attributes.get("processingLevel", ""),
            size_mb=float(item.get("ContentLength", 0)) / (1024 * 1024),
        )
    
    async def download_scene(
        self,
        scene: SentinelScene,
        output_dir: str,
        extract: bool = True,
    ) -> str:
        """
        Download a Sentinel-2 scene.
        
        Args:
            scene: SentinelScene to download
            output_dir: Directory to save the file
            extract: Whether to extract the SAFE archive
        
        Returns:
            Path to downloaded file
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        if not self.access_token:
            await self.authenticate()
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{scene.title}.SAFE.zip")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        logger.info(f"Downloading scene {scene.scene_id} ({scene.size_mb:.1f} MB)")
        
        async with self.session.get(scene.download_url, headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Download failed: {error_text}")
            
            with open(output_path, "wb") as f:
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    f.write(chunk)
        
        logger.info(f"Downloaded to {output_path}")
        
        if extract:
            import zipfile
            extract_dir = output_path.replace(".SAFE.zip", "")
            with zipfile.ZipFile(output_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            logger.info(f"Extracted to {extract_dir}")
            return extract_dir
        
        return output_path
    
    async def download_quicklook(
        self,
        scene: SentinelScene,
        output_dir: str,
    ) -> str:
        """Download quicklook image for a scene."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{scene.scene_id}_quicklook.jpg")
        
        async with self.session.get(scene.quicklook_url) as response:
            if response.status != 200:
                raise Exception(f"Quicklook download failed")
            
            with open(output_path, "wb") as f:
                f.write(await response.read())
        
        return output_path


async def download_sentinel2_for_area(
    bbox: List[float],
    start_date: str,
    end_date: str,
    output_dir: str = "data/satellite",
    cloud_cover_max: float = 30.0,
    limit: int = 5,
) -> List[str]:
    """
    Convenience function to download Sentinel-2 imagery for an area.
    
    Args:
        bbox: [west, south, east, north] bounding box
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_dir: Output directory
        cloud_cover_max: Maximum cloud cover percentage
        limit: Maximum number of scenes to download
    
    Returns:
        List of downloaded file paths
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    downloaded = []
    
    async with Sentinel2Downloader() as downloader:
        scenes = await downloader.search(
            bbox=bbox,
            start_date=start,
            end_date=end,
            cloud_cover_max=cloud_cover_max,
            limit=limit,
        )
        
        for scene in scenes:
            try:
                path = await downloader.download_scene(scene, output_dir, extract=False)
                downloaded.append(path)
            except Exception as e:
                logger.error(f"Failed to download scene {scene.scene_id}: {e}")
    
    return downloaded


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Sentinel-2 imagery")
    parser.add_argument("--bbox", required=True, help="Bounding box: west,south,east,north")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", default="data/satellite", help="Output directory")
    parser.add_argument("--cloud", type=float, default=30.0, help="Max cloud cover %%")
    parser.add_argument("--limit", type=int, default=5, help="Max scenes to download")
    
    args = parser.parse_args()
    
    bbox = [float(x) for x in args.bbox.split(",")]
    
    asyncio.run(download_sentinel2_for_area(
        bbox=bbox,
        start_date=args.start,
        end_date=args.end,
        output_dir=args.output,
        cloud_cover_max=args.cloud,
        limit=args.limit,
    ))
