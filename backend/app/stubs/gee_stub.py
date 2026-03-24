"""
Google Earth Engine API Stub

Provides mock GEE functionality for testing without
requiring GEE credentials.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from app.stubs.base import BaseStub, StubResponse


@dataclass
class MockSpectralIndex:
    """Mock spectral index result."""
    index_type: str
    value: float
    min_value: float
    max_value: float
    mean_value: float
    std_value: float
    area_sqkm: float
    date: datetime


class GEEStub(BaseStub):
    """
    Stub for Google Earth Engine API.
    
    Provides mock implementations for:
    - NDVI (Normalized Difference Vegetation Index)
    - NDBI (Normalized Difference Built-up Index)
    - MNDWI (Modified Normalized Difference Water Index)
    - Land cover classification
    - Time series analysis
    
    When real API access is obtained, swap this stub with actual
    GEE Python API implementation.
    """
    
    name = "gee_stub"
    description = "Mock Google Earth Engine API"
    
    INDEX_RANGES = {
        "NDVI": {"min": -1.0, "max": 1.0, "desc": "Vegetation health"},
        "NDBI": {"min": -1.0, "max": 1.0, "desc": "Built-up areas"},
        "MNDWI": {"min": -1.0, "max": 1.0, "desc": "Water bodies"},
        "EVI": {"min": 0.0, "max": 1.0, "desc": "Enhanced vegetation"},
        "SAVI": {"min": -1.0, "max": 1.0, "desc": "Soil-adjusted vegetation"},
        "UI": {"min": -1.0, "max": 1.0, "desc": "Urban index"},
    }
    
    LAND_COVER_CLASSES = [
        "water", "vegetation", "built_up", "agricultural", 
        "barren", "forest", "wetland"
    ]
    
    def __init__(self):
        super().__init__()
        self._results_cache: Dict[str, Any] = {}
    
    def is_available(self) -> bool:
        return True
    
    def get_mock_data(self, count: int = 10) -> List[Dict]:
        return [{"index": idx, "range": info} for idx, info in list(self.INDEX_RANGES.items())[:count]]
    
    async def compute_index(
        self,
        index_type: str,
        geometry: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        scale: int = 30,
    ) -> StubResponse:
        """
        Compute a spectral index for an area.
        
        Args:
            index_type: Type of index (NDVI, NDBI, MNDWI, etc.)
            geometry: GeoJSON geometry
            start_date: Start date
            end_date: End date
            scale: Resolution in meters
        
        Returns:
            Mock spectral index results
        """
        self.log_stub_call("compute_index", {
            "index_type": index_type,
            "start_date": str(start_date),
            "end_date": str(end_date),
        })
        
        if index_type not in self.INDEX_RANGES:
            return StubResponse(
                success=False,
                data=None,
                error=f"Unknown index type: {index_type}",
            )
        
        range_info = self.INDEX_RANGES[index_type]
        
        mock_result = MockSpectralIndex(
            index_type=index_type,
            value=round(random.uniform(-0.5, 0.8), 4),
            min_value=round(random.uniform(range_info["min"], 0), 4),
            max_value=round(random.uniform(0, range_info["max"]), 4),
            mean_value=round(random.uniform(-0.2, 0.6), 4),
            std_value=round(random.uniform(0.05, 0.3), 4),
            area_sqkm=round(random.uniform(1, 100), 2),
            date=end_date,
        )
        
        return StubResponse(
            success=True,
            data={
                "index_type": mock_result.index_type,
                "value": mock_result.value,
                "statistics": {
                    "min": mock_result.min_value,
                    "max": mock_result.max_value,
                    "mean": mock_result.mean_value,
                    "std": mock_result.std_value,
                },
                "area_sqkm": mock_result.area_sqkm,
                "date": mock_result.date.isoformat(),
                "scale_meters": scale,
                "description": range_info["desc"],
                "source": "GEE (Mock)",
            },
        )
    
    async def compute_time_series(
        self,
        index_type: str,
        geometry: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        interval: str = "monthly",
    ) -> StubResponse:
        """
        Compute time series of spectral index.
        
        Args:
            index_type: Type of index
            geometry: GeoJSON geometry
            start_date: Start date
            end_date: End date
            interval: Time interval (daily, weekly, monthly)
        
        Returns:
            Mock time series data
        """
        self.log_stub_call("compute_time_series", {
            "index_type": index_type,
            "interval": interval,
        })
        
        if interval == "daily":
            delta = timedelta(days=1)
        elif interval == "weekly":
            delta = timedelta(weeks=1)
        else:
            delta = timedelta(days=30)
        
        time_series = []
        current_date = start_date
        
        while current_date <= end_date:
            value = round(random.uniform(-0.3, 0.7), 4)
            time_series.append({
                "date": current_date.isoformat(),
                "value": value,
            })
            current_date += delta
        
        return StubResponse(
            success=True,
            data={
                "index_type": index_type,
                "interval": interval,
                "time_series": time_series[:24],
                "source": "GEE (Mock)",
            },
        )
    
    async def classify_land_cover(
        self,
        geometry: Dict[str, Any],
        date: datetime = None,
        classifier: str = "random_forest",
    ) -> StubResponse:
        """
        Classify land cover for an area.
        
        Args:
            geometry: GeoJSON geometry
            date: Date for classification
            classifier: Classification algorithm
        
        Returns:
            Mock land cover classification
        """
        self.log_stub_call("classify_land_cover", {
            "date": str(date),
            "classifier": classifier,
        })
        
        classification = {}
        remaining = 100.0
        
        for i, lc_class in enumerate(self.LAND_COVER_CLASSES[:-1]):
            percentage = round(random.uniform(5, min(40, remaining)), 1)
            classification[lc_class] = percentage
            remaining -= percentage
        
        classification[self.LAND_COVER_CLASSES[-1]] = round(remaining, 1)
        
        return StubResponse(
            success=True,
            data={
                "classification": classification,
                "dominant_class": max(classification, key=classification.get),
                "accuracy": round(random.uniform(0.75, 0.95), 2),
                "date": (date or datetime.utcnow()).isoformat(),
                "classifier": classifier,
                "source": "GEE (Mock)",
            },
        )
    
    async def detect_changes(
        self,
        geometry: Dict[str, Any],
        before_date: datetime,
        after_date: datetime,
        threshold: float = 0.1,
    ) -> StubResponse:
        """
        Detect changes between two dates.
        
        Args:
            geometry: GeoJSON geometry
            before_date: Before date
            after_date: After date
            threshold: Change threshold
        
        Returns:
            Mock change detection results
        """
        self.log_stub_call("detect_changes", {
            "before_date": str(before_date),
            "after_date": str(after_date),
        })
        
        change_types = [
            "vegetation_loss",
            "vegetation_gain",
            "urban_expansion",
            "water_body_change",
            "agricultural_change",
        ]
        
        changes = []
        for change_type in random.sample(change_types, k=random.randint(2, 4)):
            changes.append({
                "type": change_type,
                "area_sqkm": round(random.uniform(0.1, 10), 2),
                "confidence": round(random.uniform(0.6, 0.95), 2),
            })
        
        return StubResponse(
            success=True,
            data={
                "changes": changes,
                "total_changed_area_sqkm": round(sum(c["area_sqkm"] for c in changes), 2),
                "before_date": before_date.isoformat(),
                "after_date": after_date.isoformat(),
                "threshold": threshold,
                "source": "GEE (Mock)",
            },
        )
    
    async def get_image_url(
        self,
        geometry: Dict[str, Any],
        date: datetime,
        bands: List[str] = None,
        vis_params: Dict = None,
    ) -> StubResponse:
        """
        Get a map image URL for visualization.
        
        Args:
            geometry: GeoJSON geometry
            date: Image date
            bands: Bands to visualize
            vis_params: Visualization parameters
        
        Returns:
            Mock image URL
        """
        self.log_stub_call("get_image_url", {"date": str(date)})
        
        return StubResponse(
            success=True,
            data={
                "url": f"mock://gee/tiles/{date.strftime('%Y%m%d')}/{{z}}/{{x}}/{{y}}.png",
                "bands": bands or ["B4", "B3", "B2"],
                "date": date.isoformat(),
                "source": "GEE (Mock)",
            },
        )
    
    def get_available_indices(self) -> List[Dict]:
        """Get list of available spectral indices."""
        return [
            {
                "index": idx,
                "min": info["min"],
                "max": info["max"],
                "description": info["desc"],
            }
            for idx, info in self.INDEX_RANGES.items()
        ]
    
    def get_land_cover_classes(self) -> List[str]:
        """Get list of land cover classes."""
        return self.LAND_COVER_CLASSES
