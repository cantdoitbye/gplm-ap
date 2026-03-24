"""
Change Detection Agent (CDA)

Detects changes between temporal satellite/aerial imagery pairs.
Identifies new construction, expansions, demolitions, and encroachments.
"""

import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

try:
    import rasterio
    from rasterio.mask import mask
    from shapely.geometry import box, Polygon, mapping
    import geopandas as gpd
    GEOSPATIAL_AVAILABLE = True
except ImportError:
    GEOSPATIAL_AVAILABLE = False
    logger.warning("Geospatial libraries not available")


class ChangeType(str, Enum):
    """Types of detected changes."""
    NEW_CONSTRUCTION = "new_construction"
    EXPANSION = "expansion"
    DEMOLITION = "demolition"
    VEGETATION_CHANGE = "vegetation_change"
    WATER_CHANGE = "water_change"
    ROAD_CHANGE = "road_change"
    ENCROACHMENT = "encroachment"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    """Change severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ChangeArea:
    """Detected change area."""
    change_id: str
    change_type: ChangeType
    change_category: str
    confidence: float
    severity: Severity
    geometry: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None
    area_sqm: float = 0.0
    before_value: Optional[float] = None
    after_value: Optional[float] = None
    difference: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "change_type": self.change_type.value,
            "change_category": self.change_category,
            "confidence": round(self.confidence, 4),
            "severity": self.severity.value,
            "geometry": self.geometry,
            "bbox": self.bbox,
            "area_sqm": round(self.area_sqm, 2),
            "before_value": self.before_value,
            "after_value": self.after_value,
            "difference": self.difference,
        }


@dataclass
class ChangeDetectionResult:
    """Results from change detection."""
    task_id: str
    status: str
    changes: List[ChangeArea] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    comparison_stats: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    before_date: Optional[str] = None
    after_date: Optional[str] = None
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "changes": [c.to_dict() for c in self.changes],
            "summary": self.summary,
            "comparison_stats": self.comparison_stats,
            "processing_time": round(self.processing_time, 2),
            "before_date": self.before_date,
            "after_date": self.after_date,
            "created_at": self.created_at,
        }


class ChangeDetector:
    """
    Change Detection Agent for temporal imagery comparison.
    
    Detects changes between two satellite imagery dates:
    - New construction (new building footprints)
    - Building expansion (increased building area)
    - Demolition (removed buildings)
    - Vegetation changes
    - Water body changes
    - Road changes
    - Potential encroachments
    """
    
    CHANGE_THRESHOLDS = {
        "ndvi_decrease": -0.2,
        "ndbi_increase": 0.15,
        "building_area_increase": 0.3,
        "min_change_area_sqm": 50,
    }
    
    SEVERITY_RULES = {
        "critical": {"min_area": 1000, "types": ["encroachment"]},
        "high": {"min_area": 500, "types": ["new_construction", "demolition"]},
        "medium": {"min_area": 100, "types": ["expansion", "vegetation_change"]},
        "low": {"min_area": 0, "types": []},
    }
    
    def __init__(
        self,
        pixel_resolution: float = 10.0,
        min_change_area: float = None,
        confidence_threshold: float = 0.5,
    ):
        self.pixel_resolution = pixel_resolution
        self.min_change_area = min_change_area or self.CHANGE_THRESHOLDS["min_change_area_sqm"]
        self.confidence_threshold = confidence_threshold
    
    def compare(
        self,
        before_image: Any,
        after_image: Any,
        before_date: str = None,
        after_date: str = None,
        change_types: List[str] = None,
        bbox: List[float] = None,
    ) -> ChangeDetectionResult:
        """
        Compare two images and detect changes.
        
        Args:
            before_image: Before period image (path, array, or rasterio dataset)
            after_image: After period image
            before_date: Date of before image
            after_date: Date of after image
            change_types: Types of changes to detect
            bbox: Bounding box to clip comparison
        
        Returns:
            ChangeDetectionResult with detected changes
        """
        import time
        
        start_time = time.time()
        task_id = str(uuid.uuid4())
        
        if change_types is None:
            change_types = [ct.value for ct in ChangeType if ct != ChangeType.UNKNOWN]
        
        try:
            before_array, before_meta = self._load_image(before_image)
            after_array, after_meta = self._load_image(after_image)
            
            if bbox:
                before_array = self._clip_to_bbox(before_array, before_meta, bbox)
                after_array = self._clip_to_bbox(after_array, after_meta, bbox)
            
            if before_array.shape != after_array.shape:
                after_array = self._resample(after_array, before_array.shape)
            
            changes = []
            
            diff = self._compute_difference(before_array, after_array)
            
            if "new_construction" in change_types or "expansion" in change_types:
                construction_changes = self._detect_construction(before_array, after_array, diff)
                changes.extend(construction_changes)
            
            if "demolition" in change_types:
                demolition_changes = self._detect_demolition(before_array, after_array, diff)
                changes.extend(demolition_changes)
            
            if "vegetation_change" in change_types:
                veg_changes = self._detect_vegetation_change(before_array, after_array, diff)
                changes.extend(veg_changes)
            
            if "water_change" in change_types:
                water_changes = self._detect_water_change(before_array, after_array, diff)
                changes.extend(water_changes)
            
            changes = [c for c in changes if c.area_sqm >= self.min_change_area]
            
            for change in changes:
                change.severity = self._determine_severity(change)
            
            summary = self._compute_summary(changes)
            comparison_stats = self._compute_comparison_stats(before_array, after_array, diff)
            
            processing_time = time.time() - start_time
            
            logger.info(f"Change detection completed: {len(changes)} changes in {processing_time:.2f}s")
            
            return ChangeDetectionResult(
                task_id=task_id,
                status="completed",
                changes=changes,
                summary=summary,
                comparison_stats=comparison_stats,
                processing_time=processing_time,
                before_date=before_date,
                after_date=after_date,
            )
            
        except Exception as e:
            logger.error(f"Change detection failed: {e}")
            return ChangeDetectionResult(
                task_id=task_id,
                status="failed",
                summary={"error": str(e)},
                processing_time=time.time() - start_time,
            )
    
    def _load_image(self, image: Any) -> Tuple[np.ndarray, Dict]:
        """Load image from path, array, or dataset."""
        if isinstance(image, str):
            if not GEOSPATIAL_AVAILABLE:
                raise ImportError("Rasterio required for image loading")
            
            with rasterio.open(image) as src:
                array = src.read()
                meta = src.meta.copy()
            return array, meta
        
        elif isinstance(image, np.ndarray):
            return image, {}
        
        elif hasattr(image, 'read'):
            array = image.read()
            meta = image.meta.copy()
            return array, meta
        
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")
    
    def _clip_to_bbox(
        self,
        array: np.ndarray,
        meta: Dict,
        bbox: List[float],
    ) -> np.ndarray:
        """Clip array to bounding box."""
        if not meta:
            return array
        
        try:
            from rasterio.features import bounds
            
            geom = box(*bbox)
            with rasterio.open(meta.get('path', '')) if meta.get('path') else None as src:
                if src:
                    out_image, _ = mask(src, [geom], crop=True)
                    return out_image
        except Exception:
            pass
        
        return array
    
    def _resample(
        self,
        array: np.ndarray,
        target_shape: Tuple,
    ) -> np.ndarray:
        """Resample array to target shape."""
        from scipy.ndimage import zoom
        
        factors = (
            1.0,
            target_shape[1] / array.shape[1],
            target_shape[2] / array.shape[2],
        )
        
        return zoom(array, factors, order=1)
    
    def _compute_difference(
        self,
        before: np.ndarray,
        after: np.ndarray,
    ) -> np.ndarray:
        """Compute pixel-wise difference."""
        if before.shape != after.shape:
            raise ValueError("Image shapes must match")
        
        diff = after.astype(float) - before.astype(float)
        return diff
    
    def _detect_construction(
        self,
        before: np.ndarray,
        after: np.ndarray,
        diff: np.ndarray,
    ) -> List[ChangeArea]:
        """Detect new construction and expansions."""
        changes = []
        
        if diff.shape[0] >= 4:
            red_diff = diff[3] if diff.shape[0] > 3 else diff[0]
            nir_diff = diff[4] if diff.shape[0] > 4 else diff[1]
            
            with np.errstate(divide='ignore', invalid='ignore'):
                before_ndbi = self._compute_ndbi(before)
                after_ndbi = self._compute_ndbi(after)
                ndbi_change = after_ndbi - before_ndbi
            
            construction_mask = ndbi_change > self.CHANGE_THRESHOLDS["ndbi_increase"]
            
            change_regions = self._find_connected_regions(construction_mask)
            
            for region in change_regions:
                area_sqm = region['area'] * (self.pixel_resolution ** 2)
                
                change_type = ChangeType.NEW_CONSTRUCTION if region['new'] else ChangeType.EXPANSION
                
                change = ChangeArea(
                    change_id=str(uuid.uuid4()),
                    change_type=change_type,
                    change_category="built_up",
                    confidence=min(0.9, 0.5 + abs(ndbi_change[region['center']].mean()) * 2),
                    severity=Severity.MEDIUM,
                    bbox=region['bbox'],
                    area_sqm=area_sqm,
                    before_value=float(before_ndbi[region['center']].mean()) if before_ndbi.any() else 0,
                    after_value=float(after_ndbi[region['center']].mean()) if after_ndbi.any() else 0,
                )
                changes.append(change)
        
        return changes
    
    def _detect_demolition(
        self,
        before: np.ndarray,
        after: np.ndarray,
        diff: np.ndarray,
    ) -> List[ChangeArea]:
        """Detect demolitions."""
        changes = []
        
        if diff.shape[0] >= 4:
            before_ndbi = self._compute_ndbi(before)
            after_ndbi = self._compute_ndbi(after)
            ndbi_change = after_ndbi - before_ndbi
            
            demolition_mask = ndbi_change < -self.CHANGE_THRESHOLDS["ndbi_increase"]
            
            change_regions = self._find_connected_regions(demolition_mask)
            
            for region in change_regions:
                area_sqm = region['area'] * (self.pixel_resolution ** 2)
                
                change = ChangeArea(
                    change_id=str(uuid.uuid4()),
                    change_type=ChangeType.DEMOLITION,
                    change_category="built_up",
                    confidence=min(0.85, 0.5 + abs(ndbi_change[region['center']].mean())),
                    severity=Severity.HIGH,
                    bbox=region['bbox'],
                    area_sqm=area_sqm,
                    before_value=float(before_ndbi[region['center']].mean()) if before_ndbi.any() else 0,
                    after_value=float(after_ndbi[region['center']].mean()) if after_ndbi.any() else 0,
                )
                changes.append(change)
        
        return changes
    
    def _detect_vegetation_change(
        self,
        before: np.ndarray,
        after: np.ndarray,
        diff: np.ndarray,
    ) -> List[ChangeArea]:
        """Detect vegetation changes."""
        changes = []
        
        if diff.shape[0] >= 5:
            before_ndvi = self._compute_ndvi(before)
            after_ndvi = self._compute_ndvi(after)
            ndvi_change = after_ndvi - before_ndvi
            
            veg_loss_mask = ndvi_change < self.CHANGE_THRESHOLDS["ndvi_decrease"]
            veg_gain_mask = ndvi_change > -self.CHANGE_THRESHOLDS["ndvi_decrease"]
            
            for mask, is_loss in [(veg_loss_mask, True), (veg_gain_mask, False)]:
                change_regions = self._find_connected_regions(mask)
                
                for region in change_regions:
                    area_sqm = region['area'] * (self.pixel_resolution ** 2)
                    
                    change = ChangeArea(
                        change_id=str(uuid.uuid4()),
                        change_type=ChangeType.VEGETATION_CHANGE,
                        change_category="vegetation_loss" if is_loss else "vegetation_gain",
                        confidence=0.7,
                        severity=Severity.LOW,
                        bbox=region['bbox'],
                        area_sqm=area_sqm,
                        before_value=float(before_ndvi[region['center']].mean()) if before_ndvi.any() else 0,
                        after_value=float(after_ndvi[region['center']].mean()) if after_ndvi.any() else 0,
                    )
                    changes.append(change)
        
        return changes
    
    def _detect_water_change(
        self,
        before: np.ndarray,
        after: np.ndarray,
        diff: np.ndarray,
    ) -> List[ChangeArea]:
        """Detect water body changes."""
        changes = []
        
        if diff.shape[0] >= 5:
            before_mndwi = self._compute_mndwi(before)
            after_mndwi = self._compute_mndwi(after)
            mndwi_change = after_mndwi - before_mndwi
            
            water_change_mask = np.abs(mndwi_change) > 0.2
            
            change_regions = self._find_connected_regions(water_change_mask)
            
            for region in change_regions:
                area_sqm = region['area'] * (self.pixel_resolution ** 2)
                
                change = ChangeArea(
                    change_id=str(uuid.uuid4()),
                    change_type=ChangeType.WATER_CHANGE,
                    change_category="water_gain" if mndwi_change[region['center']].mean() > 0 else "water_loss",
                    confidence=0.75,
                    severity=Severity.MEDIUM,
                    bbox=region['bbox'],
                    area_sqm=area_sqm,
                )
                changes.append(change)
        
        return changes
    
    def _compute_ndvi(self, image: np.ndarray) -> np.ndarray:
        """Compute NDVI from image bands."""
        if image.shape[0] >= 5:
            red = image[3].astype(float)
            nir = image[4].astype(float)
            
            with np.errstate(divide='ignore', invalid='ignore'):
                ndvi = np.where(
                    (nir + red) == 0,
                    0,
                    (nir - red) / (nir + red)
                )
            return ndvi
        return np.zeros(image.shape[1:])
    
    def _compute_ndbi(self, image: np.ndarray) -> np.ndarray:
        """Compute NDBI from image bands."""
        if image.shape[0] >= 6:
            nir = image[4].astype(float)
            swir = image[5].astype(float)
            
            with np.errstate(divide='ignore', invalid='ignore'):
                ndbi = np.where(
                    (swir + nir) == 0,
                    0,
                    (swir - nir) / (swir + nir)
                )
            return ndbi
        return np.zeros(image.shape[1:])
    
    def _compute_mndwi(self, image: np.ndarray) -> np.ndarray:
        """Compute MNDWI from image bands."""
        if image.shape[0] >= 6:
            green = image[2].astype(float)
            swir = image[5].astype(float)
            
            with np.errstate(divide='ignore', invalid='ignore'):
                mndwi = np.where(
                    (green + swir) == 0,
                    0,
                    (green - swir) / (green + swir)
                )
            return mndwi
        return np.zeros(image.shape[1:])
    
    def _find_connected_regions(self, mask: np.ndarray) -> List[Dict]:
        """Find connected regions in a binary mask."""
        try:
            from scipy import ndimage
            
            labeled, num_features = ndimage.label(mask)
            regions = []
            
            for i in range(1, num_features + 1):
                region_mask = labeled == i
                area = np.sum(region_mask)
                
                if area < 3:
                    continue
                
                coords = np.where(region_mask)
                center = (coords[0].mean(), coords[1].mean())
                
                y_min, y_max = coords[0].min(), coords[0].max()
                x_min, x_max = coords[1].min(), coords[1].max()
                
                regions.append({
                    'area': area,
                    'center': (int(center[0]), int(center[1])),
                    'bbox': [float(x_min), float(y_min), float(x_max), float(y_max)],
                    'new': True,
                })
            
            return regions
            
        except ImportError:
            return []
    
    def _determine_severity(self, change: ChangeArea) -> Severity:
        """Determine severity level for a change."""
        for severity, rules in self.SEVERITY_RULES.items():
            if change.change_type.value in rules.get("types", []):
                if change.area_sqm >= rules.get("min_area", 0):
                    return Severity(severity)
            elif change.area_sqm >= rules.get("min_area", float('inf')):
                return Severity(severity)
        
        return Severity.LOW
    
    def _compute_summary(self, changes: List[ChangeArea]) -> Dict[str, Any]:
        """Compute summary statistics."""
        by_type = {}
        by_severity = {s.value: 0 for s in Severity}
        total_area = 0
        
        for change in changes:
            ctype = change.change_type.value
            if ctype not in by_type:
                by_type[ctype] = {"count": 0, "total_area": 0}
            
            by_type[ctype]["count"] += 1
            by_type[ctype]["total_area"] += change.area_sqm
            by_severity[change.severity.value] += 1
            total_area += change.area_sqm
        
        return {
            "total_changes": len(changes),
            "total_area_sqm": round(total_area, 2),
            "by_type": by_type,
            "by_severity": by_severity,
        }
    
    def _compute_comparison_stats(
        self,
        before: np.ndarray,
        after: np.ndarray,
        diff: np.ndarray,
    ) -> Dict[str, Any]:
        """Compute comparison statistics."""
        return {
            "before_shape": list(before.shape),
            "after_shape": list(after.shape),
            "diff_mean": float(np.mean(diff)),
            "diff_std": float(np.std(diff)),
            "diff_min": float(np.min(diff)),
            "diff_max": float(np.max(diff)),
        }


class MockChangeDetector:
    """Mock change detector for testing."""
    
    def __init__(self):
        self.pixel_resolution = 10.0
        logger.info("Initialized MockChangeDetector")
    
    def compare(
        self,
        before_image: Any,
        after_image: Any,
        before_date: str = None,
        after_date: str = None,
        change_types: List[str] = None,
        bbox: List[float] = None,
    ) -> ChangeDetectionResult:
        import time
        import random
        
        start_time = time.time()
        task_id = str(uuid.uuid4())
        
        changes = []
        
        random.seed(42)
        
        num_new_construction = random.randint(2, 5)
        num_expansions = random.randint(1, 3)
        num_demolitions = random.randint(0, 2)
        num_vegetation = random.randint(3, 8)
        
        for i in range(num_new_construction):
            change = ChangeArea(
                change_id=str(uuid.uuid4()),
                change_type=ChangeType.NEW_CONSTRUCTION,
                change_category="built_up",
                confidence=random.uniform(0.7, 0.95),
                severity=Severity.HIGH,
                bbox=[random.uniform(0, 1000) for _ in range(4)],
                area_sqm=random.uniform(100, 2000),
                before_value=0.1,
                after_value=0.6,
            )
            changes.append(change)
        
        for i in range(num_expansions):
            change = ChangeArea(
                change_id=str(uuid.uuid4()),
                change_type=ChangeType.EXPANSION,
                change_category="built_up",
                confidence=random.uniform(0.65, 0.85),
                severity=Severity.MEDIUM,
                bbox=[random.uniform(0, 1000) for _ in range(4)],
                area_sqm=random.uniform(50, 500),
            )
            changes.append(change)
        
        for i in range(num_demolitions):
            change = ChangeArea(
                change_id=str(uuid.uuid4()),
                change_type=ChangeType.DEMOLITION,
                change_category="built_up",
                confidence=random.uniform(0.6, 0.8),
                severity=Severity.HIGH,
                bbox=[random.uniform(0, 1000) for _ in range(4)],
                area_sqm=random.uniform(100, 800),
            )
            changes.append(change)
        
        for i in range(num_vegetation):
            change = ChangeArea(
                change_id=str(uuid.uuid4()),
                change_type=ChangeType.VEGETATION_CHANGE,
                change_category="vegetation_loss",
                confidence=random.uniform(0.5, 0.75),
                severity=Severity.LOW,
                bbox=[random.uniform(0, 1000) for _ in range(4)],
                area_sqm=random.uniform(200, 5000),
            )
            changes.append(change)
        
        summary = {
            "total_changes": len(changes),
            "total_area_sqm": sum(c.area_sqm for c in changes),
            "by_type": {
                "new_construction": {"count": num_new_construction},
                "expansion": {"count": num_expansions},
                "demolition": {"count": num_demolitions},
                "vegetation_change": {"count": num_vegetation},
            },
            "by_severity": {
                "critical": 0,
                "high": num_new_construction + num_demolitions,
                "medium": num_expansions,
                "low": num_vegetation,
            },
        }
        
        return ChangeDetectionResult(
            task_id=task_id,
            status="completed",
            changes=changes,
            summary=summary,
            comparison_stats={
                "diff_mean": 0.15,
                "diff_std": 0.08,
            },
            processing_time=time.time() - start_time,
            before_date=before_date,
            after_date=after_date,
        )


def get_change_detector(use_mock: bool = False) -> ChangeDetector:
    if use_mock:
        return MockChangeDetector()
    return ChangeDetector()
