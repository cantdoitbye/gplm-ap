"""
Property Detection Agent (PDA)

Detects buildings, roads, water bodies from satellite/aerial imagery
using YOLOv8 computer vision models.
"""

import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
    from PIL import Image
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("Ultralytics not installed. Install with: pip install ultralytics")


@dataclass
class Detection:
    """Single detection result."""
    detection_id: str
    detection_type: str
    confidence: float
    bbox: List[float]
    polygon: Optional[List[Tuple[float, float]]] = None
    area_sqm: Optional[float] = None
    centroid: Optional[Tuple[float, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detection_id": self.detection_id,
            "detection_type": self.detection_type,
            "confidence": round(self.confidence, 4),
            "bbox": self.bbox,
            "polygon": self.polygon,
            "area_sqm": self.area_sqm,
            "centroid": self.centroid,
        }


@dataclass
class DetectionResult:
    """Results from property detection."""
    task_id: str
    status: str
    detections: List[Detection] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    processing_time: float = 0.0
    model_name: str = ""
    model_version: str = ""
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "detections": [d.to_dict() for d in self.detections],
            "summary": self.summary,
            "processing_time": self.processing_time,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "created_at": self.created_at,
        }


class PropertyDetector:
    """
    Property Detection Agent using YOLOv8.
    
    Detects:
    - Buildings
    - Roads
    - Water bodies
    
    from satellite/aerial imagery.
    """
    
    CLASS_MAPPING = {
        0: "building",
        1: "road",
        2: "water",
        3: "vegetation",
        4: "agricultural",
    }
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None,
        confidence_threshold: float = None,
    ):
        if not YOLO_AVAILABLE:
            raise ImportError("Ultralytics YOLOv8 not available")
        
        self.model_path = model_path or settings.YOLO_MODEL_PATH
        self.device = device or settings.MODEL_DEVICE
        self.confidence_threshold = confidence_threshold or settings.MODEL_CONFIDENCE_THRESHOLD
        
        self.model = None
        self.model_name = "yolov8n"
        self.model_version = "8.1.0"
        
        self._load_model()
    
    def _load_model(self):
        """Load YOLOv8 model."""
        if os.path.exists(self.model_path):
            logger.info(f"Loading custom model from {self.model_path}")
            self.model = YOLO(self.model_path)
            self.model_name = os.path.basename(self.model_path).replace(".pt", "")
        else:
            logger.info(f"Loading pretrained YOLOv8 model")
            self.model = YOLO("yolov8n.pt")
            self.model_name = "yolov8n"
    
    def detect(
        self,
        image: Any,
        detection_types: List[str] = None,
        confidence_threshold: float = None,
        return_polygons: bool = True,
    ) -> DetectionResult:
        import time
        
        start_time = time.time()
        task_id = str(uuid.uuid4())
        
        if detection_types is None:
            detection_types = ["building", "road", "water"]
        
        conf = confidence_threshold or self.confidence_threshold
        
        try:
            results = self.model(
                image,
                device=self.device,
                conf=conf,
                verbose=False,
            )
            
            detections = []
            
            for result in results:
                boxes = result.boxes
                
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i])
                    cls_name = self.CLASS_MAPPING.get(cls_id, f"class_{cls_id}")
                    
                    if cls_name not in detection_types:
                        continue
                    
                    confidence = float(boxes.conf[i])
                    
                    xyxy = boxes.xyxy[i].cpu().numpy()
                    bbox = [float(x) for x in xyxy]
                    
                    polygon = None
                    area_sqm = None
                    centroid = None
                    
                    if return_polygons and result.masks is not None:
                        mask = result.masks.data[i].cpu().numpy()
                        polygon = self._mask_to_polygon(mask)
                        area_sqm = self._compute_area(polygon, result.orig_shape)
                        centroid = self._compute_centroid(polygon)
                    else:
                        area_sqm = self._compute_bbox_area(bbox, result.orig_shape)
                        centroid = self._compute_bbox_centroid(bbox)
                    
                    detection = Detection(
                        detection_id=str(uuid.uuid4()),
                        detection_type=cls_name,
                        confidence=confidence,
                        bbox=bbox,
                        polygon=polygon,
                        area_sqm=area_sqm,
                        centroid=centroid,
                    )
                    detections.append(detection)
            
            summary = self._compute_summary(detections)
            processing_time = time.time() - start_time
            
            result = DetectionResult(
                task_id=task_id,
                status="completed",
                detections=detections,
                summary=summary,
                processing_time=processing_time,
                model_name=self.model_name,
                model_version=self.model_version,
            )
            
            logger.info(f"Detection completed: {len(detections)} objects found in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Detection failed: {e}")
            return DetectionResult(
                task_id=task_id,
                status="failed",
                summary={"error": str(e)},
                processing_time=time.time() - start_time,
            )
    
    def _mask_to_polygon(self, mask: np.ndarray) -> List[Tuple[float, float]]:
        try:
            import cv2
            mask_uint8 = (mask * 255).astype(np.uint8)
            contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                largest = max(contours, key=cv2.contourArea)
                polygon = [(float(pt[0][0]), float(pt[0][1])) for pt in largest]
                return polygon
        except Exception as e:
            logger.warning(f"Could not convert mask to polygon: {e}")
        
        return None
    
    def _compute_area(self, polygon: List[Tuple[float, float]], image_shape: Tuple[int, int]) -> float:
        if not polygon:
            return None
        
        try:
            from shapely.geometry import Polygon as ShapelyPolygon
            poly = ShapelyPolygon(polygon)
            pixel_area = poly.area
            
            resolution = 10.0
            area_sqm = pixel_area * (resolution ** 2)
            return round(area_sqm, 2)
        except Exception:
            return None
    
    def _compute_bbox_area(self, bbox: List[float], image_shape: Tuple[int, int]) -> float:
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        pixel_area = width * height
        
        resolution = 10.0
        return round(pixel_area * (resolution ** 2), 2)
    
    def _compute_centroid(self, polygon: List[Tuple[float, float]]) -> Tuple[float, float]:
        if not polygon:
            return None
        
        x_coords = [p[0] for p in polygon]
        y_coords = [p[1] for p in polygon]
        
        return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))
    
    def _compute_bbox_centroid(self, bbox: List[float]) -> Tuple[float, float]:
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    
    def _compute_summary(self, detections: List[Detection]) -> Dict[str, Any]:
        by_type = {}
        
        for det in detections:
            dtype = det.detection_type
            if dtype not in by_type:
                by_type[dtype] = {
                    "count": 0,
                    "total_area_sqm": 0,
                    "avg_confidence": 0,
                }
            
            by_type[dtype]["count"] += 1
            if det.area_sqm:
                by_type[dtype]["total_area_sqm"] += det.area_sqm
            by_type[dtype]["avg_confidence"] += det.confidence
        
        for dtype in by_type:
            count = by_type[dtype]["count"]
            if count > 0:
                by_type[dtype]["avg_confidence"] = round(by_type[dtype]["avg_confidence"] / count, 4)
                by_type[dtype]["total_area_sqm"] = round(by_type[dtype]["total_area_sqm"], 2)
        
        return {
            "total_detections": len(detections),
            "by_type": by_type,
        }


class MockPropertyDetector:
    """Mock detector for testing without model weights."""
    
    def __init__(self):
        self.model_name = "mock_detector"
        self.model_version = "1.0.0"
        logger.info("Initialized MockPropertyDetector")
    
    def detect(
        self,
        image: Any,
        detection_types: List[str] = None,
        confidence_threshold: float = 0.5,
    ) -> DetectionResult:
        import time
        import random
        
        start_time = time.time()
        task_id = str(uuid.uuid4())
        
        if detection_types is None:
            detection_types = ["building", "road", "water"]
        
        detections = []
        
        try:
            if isinstance(image, str) and os.path.exists(image):
                img = Image.open(image)
                width, height = img.size
            elif isinstance(image, np.ndarray):
                height, width = image.shape[:2]
            else:
                width, height = 1000, 1000
            
            random.seed(42)
            
            num_buildings = random.randint(10, 30)
            num_roads = random.randint(2, 5)
            num_water = random.randint(0, 3)
            
            for i in range(num_buildings):
                if "building" not in detection_types:
                    continue
                
                x = random.randint(50, width - 100)
                y = random.randint(50, height - 100)
                w = random.randint(20, 80)
                h = random.randint(20, 80)
                
                detection = Detection(
                    detection_id=str(uuid.uuid4()),
                    detection_type="building",
                    confidence=random.uniform(0.6, 0.99),
                    bbox=[x, y, x + w, y + h],
                    area_sqm=random.uniform(50, 500),
                    centroid=(x + w/2, y + h/2),
                )
                detections.append(detection)
            
            for i in range(num_roads):
                if "road" not in detection_types:
                    continue
                
                y = random.randint(100, height - 100)
                w = random.randint(200, 500)
                h = random.randint(10, 30)
                
                detection = Detection(
                    detection_id=str(uuid.uuid4()),
                    detection_type="road",
                    confidence=random.uniform(0.7, 0.95),
                    bbox=[50, y, 50 + w, y + h],
                    area_sqm=w * h * 10,
                    centroid=(50 + w/2, y + h/2),
                )
                detections.append(detection)
            
            for i in range(num_water):
                if "water" not in detection_types:
                    continue
                
                x = random.randint(100, width - 200)
                y = random.randint(100, height - 200)
                w = random.randint(100, 200)
                h = random.randint(80, 150)
                
                detection = Detection(
                    detection_id=str(uuid.uuid4()),
                    detection_type="water",
                    confidence=random.uniform(0.65, 0.9),
                    bbox=[x, y, x + w, y + h],
                    area_sqm=random.uniform(1000, 5000),
                    centroid=(x + w/2, y + h/2),
                )
                detections.append(detection)
            
            summary = {
                "total_detections": len(detections),
                "by_type": {
                    "building": {"count": num_buildings, "avg_confidence": 0.82},
                    "road": {"count": num_roads, "avg_confidence": 0.85},
                    "water": {"count": num_water, "avg_confidence": 0.78},
                },
            }
            
            return DetectionResult(
                task_id=task_id,
                status="completed",
                detections=detections,
                summary=summary,
                processing_time=time.time() - start_time,
                model_name=self.model_name,
                model_version=self.model_version,
            )
            
        except Exception as e:
            logger.error(f"Mock detection failed: {e}")
            return DetectionResult(
                task_id=task_id,
                status="failed",
                summary={"error": str(e)},
                processing_time=time.time() - start_time,
            )


def get_detector(use_mock: bool = False):
    if use_mock or not YOLO_AVAILABLE:
        return MockPropertyDetector()
    return PropertyDetector()
