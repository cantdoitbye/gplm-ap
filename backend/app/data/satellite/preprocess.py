"""
Imagery Preprocessing Module

Handles preprocessing of satellite imagery including:
- Atmospheric correction
- Cloud masking
- Resampling
- Clipping to AOI
"""

import os
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.enums import Resampling as ResamplingEnum
from typing import Dict, List, Optional, Tuple, Any
import geopandas as gpd
from shapely.geometry import box, mapping
import logging

logger = logging.getLogger(__name__)


class ImageryPreprocessor:
    """
    Preprocessor for satellite imagery.
    """
    
    def __init__(self, output_dir: str = "data/processed"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def clip_to_aoi(
        self,
        input_path: str,
        aoi: Any,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Clip raster to area of interest.
        
        Args:
            input_path: Path to input raster
            aoi: Area of interest (GeoDataFrame, shapely geometry, or bbox tuple)
            output_path: Output path (optional)
        
        Returns:
            Path to clipped raster
        """
        if output_path is None:
            base = os.path.splitext(os.path.basename(input_path))[0]
            output_path = os.path.join(self.output_dir, f"{base}_clipped.tif")
        
        if isinstance(aoi, tuple):
            aoi_geom = box(*aoi)
            shapes = [mapping(aoi_geom)]
        elif isinstance(aoi, gpd.GeoDataFrame):
            shapes = [mapping(geom) for geom in aoi.geometry]
        else:
            shapes = [mapping(aoi)]
        
        with rasterio.open(input_path) as src:
            out_image, out_transform = mask(src, shapes, crop=True)
            out_meta = src.meta.copy()
        
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
        })
        
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_image)
        
        logger.info(f"Clipped imagery saved to {output_path}")
        return output_path
    
    def resample(
        self,
        input_path: str,
        target_resolution: float,
        output_path: Optional[str] = None,
        resampling_method: str = "bilinear",
    ) -> str:
        """
        Resample raster to target resolution.
        
        Args:
            input_path: Path to input raster
            target_resolution: Target resolution in CRS units
            output_path: Output path (optional)
            resampling_method: Resampling method (nearest, bilinear, cubic)
        
        Returns:
            Path to resampled raster
        """
        if output_path is None:
            base = os.path.splitext(os.path.basename(input_path))[0]
            output_path = os.path.join(self.output_dir, f"{base}_resampled.tif")
        
        method_map = {
            "nearest": ResamplingEnum.nearest,
            "bilinear": ResamplingEnum.bilinear,
            "cubic": ResamplingEnum.cubic,
        }
        resample = method_map.get(resampling_method, ResamplingEnum.bilinear)
        
        with rasterio.open(input_path) as src:
            transform, width, height = calculate_default_transform(
                src.crs,
                src.crs,
                src.width,
                src.height,
                *src.bounds,
                resolution=(target_resolution, target_resolution),
            )
            
            kwargs = src.meta.copy()
            kwargs.update({
                "transform": transform,
                "width": width,
                "height": height,
            })
            
            with rasterio.open(output_path, "w", **kwargs) as dst:
                for band in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, band),
                        destination=rasterio.band(dst, band),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=src.crs,
                        resampling=resample,
                    )
        
        logger.info(f"Resampled imagery saved to {output_path}")
        return output_path
    
    def calculate_ndvi(
        self,
        red_path: str,
        nir_path: str,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Calculate NDVI from red and NIR bands.
        
        NDVI = (NIR - Red) / (NIR + Red)
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, "ndvi.tif")
        
        with rasterio.open(red_path) as red_src:
            red = red_src.read(1).astype(float)
            meta = red_src.meta.copy()
        
        with rasterio.open(nir_path) as nir_src:
            nir = nir_src.read(1).astype(float)
        
        with np.errstate(divide="ignore", invalid="ignore"):
            ndvi = np.where(
                (nir + red) == 0,
                0,
                (nir - red) / (nir + red),
            )
        
        meta.update({
            "count": 1,
            "dtype": "float32",
            "nodata": None,
        })
        
        with rasterio.open(output_path, "w", **meta) as dst:
            dst.write(ndvi.astype(np.float32), 1)
        
        logger.info(f"NDVI saved to {output_path}")
        return output_path
    
    def calculate_ndbi(
        self,
        swir_path: str,
        nir_path: str,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Calculate NDBI (Built-up Index) from SWIR and NIR bands.
        
        NDBI = (SWIR - NIR) / (SWIR + NIR)
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, "ndbi.tif")
        
        with rasterio.open(swir_path) as swir_src:
            swir = swir_src.read(1).astype(float)
            meta = swir_src.meta.copy()
        
        with rasterio.open(nir_path) as nir_src:
            nir = nir_src.read(1).astype(float)
        
        with np.errstate(divide="ignore", invalid="ignore"):
            ndbi = np.where(
                (swir + nir) == 0,
                0,
                (swir - nir) / (swir + nir),
            )
        
        meta.update({
            "count": 1,
            "dtype": "float32",
            "nodata": None,
        })
        
        with rasterio.open(output_path, "w", **meta) as dst:
            dst.write(ndbi.astype(np.float32), 1)
        
        return output_path
    
    def get_statistics(self, raster_path: str) -> Dict[str, float]:
        """Get basic statistics for a raster."""
        with rasterio.open(raster_path) as src:
            data = src.read(1)
            valid_data = data[~src.nodata_mask] if src.nodata else data
            
            return {
                "min": float(np.min(valid_data)),
                "max": float(np.max(valid_data)),
                "mean": float(np.mean(valid_data)),
                "std": float(np.std(valid_data)),
                "median": float(np.median(valid_data)),
                "width": src.width,
                "height": src.height,
                "crs": str(src.crs),
                "bounds": list(src.bounds),
            }
