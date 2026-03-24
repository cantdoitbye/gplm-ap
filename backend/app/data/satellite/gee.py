"""
Google Earth Engine Integration for Satellite Imagery Processing

This module provides integration with Google Earth Engine for advanced
satellite imagery processing and analysis.

Usage:
    from app.data.satellite.gee import GoogleEarthEngineProcessor
    
    processor = GoogleEarthEngineProcessor()
    imagery = processor.get_sentinel2_composite(aoi, start_date, end_date)
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import logging

from app.config import settings

logger = logging.getLogger(__name__)

try:
    import ee
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False
    logger.warning("Google Earth Engine not installed. Install with: pip install earthengine-api")


class GoogleEarthEngineProcessor:
    """
    Google Earth Engine processor for satellite imagery.
    
    Provides methods for:
    - Sentinel-2 imagery access and processing
    - Cloud masking
    - Spectral indices calculation (NDVI, NDBI, etc.)
    - Change detection preprocessing
    """
    
    def __init__(self, service_account_key: Optional[str] = None):
        """
        Initialize GEE processor.
        
        Args:
            service_account_key: Path to service account JSON key file
        """
        if not EE_AVAILABLE:
            raise ImportError("Google Earth Engine API not available")
        
        self.initialized = False
        self.service_account_key = service_account_key or settings.GOOGLE_EARTH_ENGINE_KEY
        
        if self.service_account_key and os.path.exists(self.service_account_key):
            self._authenticate_service_account()
        else:
            self._authenticate_user()
    
    def _authenticate_service_account(self):
        """Authenticate using service account."""
        try:
            credentials = ee.ServiceAccountCredentials(None, self.service_account_key)
            ee.Initialize(credentials)
            self.initialized = True
            logger.info("Initialized Google Earth Engine with service account")
        except Exception as e:
            logger.error(f"Service account authentication failed: {e}")
    
    def _authenticate_user(self):
        """Authenticate using user credentials (requires interactive auth)."""
        try:
            ee.Initialize()
            self.initialized = True
            logger.info("Initialized Google Earth Engine")
        except Exception as e:
            logger.warning(f"Google Earth Engine initialization failed: {e}")
            logger.info("Run 'earthengine authenticate' to set up credentials")
    
    def get_sentinel2_collection(
        self,
        aoi: ee.Geometry,
        start_date: str,
        end_date: str,
        cloud_cover_max: float = 30.0,
    ) -> ee.ImageCollection:
        """
        Get Sentinel-2 image collection for area and time range.
        
        Args:
            aoi: Earth Engine geometry for area of interest
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            cloud_cover_max: Maximum cloud cover percentage
        
        Returns:
            Filtered image collection
        """
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_cover_max))
        )
        
        return collection
    
    def mask_clouds(self, image: ee.Image) -> ee.Image:
        """
        Mask clouds in Sentinel-2 image using QA60 band.
        
        Args:
            image: Sentinel-2 image
        
        Returns:
            Cloud-masked image
        """
        qa = image.select("QA60")
        
        cloud_bit_mask = 1 << 10
        cirrus_bit_mask = 1 << 11
        
        mask = (
            qa.bitwiseAnd(cloud_bit_mask)
            .eq(0)
            .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
        )
        
        return image.updateMask(mask).divide(10000)
    
    def add_spectral_indices(self, image: ee.Image) -> ee.Image:
        """
        Add spectral indices to image.
        
        Indices added:
        - NDVI: Normalized Difference Vegetation Index
        - NDBI: Normalized Difference Built-up Index
        - MNDWI: Modified Normalized Difference Water Index
        - BSI: Bare Soil Index
        
        Args:
            image: Sentinel-2 image
        
        Returns:
            Image with added spectral index bands
        """
        ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
        ndbi = image.normalizedDifference(["B11", "B8"]).rename("NDBI")
        mndwi = image.normalizedDifference(["B3", "B11"]).rename("MNDWI")
        bsi = (
            image.expression(
                "((X + Y) - (A + B)) / ((X + Y) + (A + B))",
                {
                    "X": image.select("B11"),
                    "Y": image.select("B4"),
                    "A": image.select("B8"),
                    "B": image.select("B2"),
                },
            )
            .rename("BSI")
        )
        
        return image.addBands([ndvi, ndbi, mndwi, bsi])
    
    def create_composite(
        self,
        aoi: ee.Geometry,
        start_date: str,
        end_date: str,
        cloud_cover_max: float = 30.0,
        composite_method: str = "median",
    ) -> ee.Image:
        """
        Create cloud-free composite from Sentinel-2 collection.
        
        Args:
            aoi: Area of interest geometry
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            cloud_cover_max: Maximum cloud cover percentage
            composite_method: Aggregation method (median, mean, min, max)
        
        Returns:
            Composite image
        """
        collection = self.get_sentinel2_collection(aoi, start_date, end_date, cloud_cover_max)
        collection = collection.map(self.mask_clouds)
        collection = collection.map(self.add_spectral_indices)
        
        if composite_method == "median":
            composite = collection.median()
        elif composite_method == "mean":
            composite = collection.mean()
        elif composite_method == "min":
            composite = collection.min()
        elif composite_method == "max":
            composite = collection.max()
        else:
            composite = collection.median()
        
        return composite.clip(aoi)
    
    def get_change_detection_pair(
        self,
        aoi: ee.Geometry,
        before_start: str,
        before_end: str,
        after_start: str,
        after_end: str,
    ) -> Tuple[ee.Image, ee.Image]:
        """
        Get image pair for change detection.
        
        Args:
            aoi: Area of interest
            before_start: Before period start date
            before_end: Before period end date
            after_start: After period start date
            after_end: After period end date
        
        Returns:
            Tuple of (before_image, after_image)
        """
        before = self.create_composite(aoi, before_start, before_end)
        after = self.create_composite(aoi, after_start, after_end)
        
        return before, after
    
    def compute_difference(
        self,
        before: ee.Image,
        after: ee.Image,
        bands: List[str] = None,
    ) -> ee.Image:
        """
        Compute difference between two images.
        
        Args:
            before: Before image
            after: After image
            bands: Bands to include in difference
        
        Returns:
            Difference image
        """
        if bands is None:
            bands = ["B2", "B3", "B4", "B8", "NDVI", "NDBI", "MNDWI"]
        
        diff = after.select(bands).subtract(before.select(bands))
        
        return diff
    
    def export_to_drive(
        self,
        image: ee.Image,
        description: str,
        aoi: ee.Geometry,
        scale: float = 10,
        folder: str = "AIKOSH5",
    ) -> ee.batch.Task:
        """
        Export image to Google Drive.
        
        Args:
            image: Image to export
            description: Export description
            aoi: Area of interest
            scale: Export scale in meters
            folder: Google Drive folder
        
        Returns:
            Export task
        """
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=description,
            scale=scale,
            region=aoi,
            folder=folder,
            crs="EPSG:4326",
            maxPixels=1e13,
        )
        
        return task
    
    def get_thumbnail_url(
        self,
        image: ee.Image,
        aoi: ee.Geometry,
        bands: List[str] = None,
        dimensions: int = 512,
    ) -> str:
        """
        Get thumbnail URL for image visualization.
        
        Args:
            image: Image to visualize
            aoi: Area of interest
            bands: Bands to display
            dimensions: Image dimensions
        
        Returns:
            Thumbnail URL
        """
        if bands is None:
            bands = ["B4", "B3", "B2"]
        
        vis_params = {
            "bands": bands,
            "min": 0,
            "max": 0.3,
            "dimensions": dimensions,
            "region": aoi,
        }
        
        return image.getThumbURL(vis_params)


def create_aoi_from_bbox(
    west: float,
    south: float,
    east: float,
    north: float,
) -> ee.Geometry:
    """
    Create Earth Engine geometry from bounding box.
    
    Args:
        west: West longitude
        south: South latitude
        east: East longitude
        north: North latitude
    
    Returns:
        Earth Engine geometry
    """
    return ee.Geometry.Rectangle([west, south, east, north])


def create_aoi_from_geojson(geojson: Dict[str, Any]) -> ee.Geometry:
    """
    Create Earth Engine geometry from GeoJSON.
    
    Args:
        geojson: GeoJSON dictionary
    
    Returns:
        Earth Engine geometry
    """
    return ee.Geometry(geojson)


if __name__ == "__main__":
    if not EE_AVAILABLE:
        print("Google Earth Engine API not available")
        print("Install with: pip install earthengine-api")
        print("Then run: earthengine authenticate")
        exit(1)
    
    processor = GoogleEarthEngineProcessor()
    
    aoi = create_aoi_from_bbox(
        west=80.5,
        south=16.4,
        east=80.8,
        north=16.6,
    )
    
    composite = processor.create_composite(
        aoi=aoi,
        start_date="2024-01-01",
        end_date="2024-03-31",
    )
    
    url = processor.get_thumbnail_url(composite, aoi)
    print(f"Thumbnail URL: {url}")
