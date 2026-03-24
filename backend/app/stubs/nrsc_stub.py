"""
NRSC API Stub

Provides mock high-resolution satellite imagery data from 
National Remote Sensing Centre (NRSC).

Real API: https://bhuvan.nrsc.gov.in/nrsc
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from app.stubs.base import BaseStub, StubResponse


@dataclass
class MockNRSCScene:
    """Mock NRSC high-resolution scene metadata."""
    scene_id: str
    product_id: str
    satellite: str
    sensor: str
    acquisition_date: datetime
    cloud_cover: float
    resolution: float
    geometry: Dict[str, Any]
    download_url: str
    preview_url: str
    file_size_mb: float
    order_required: bool


class NRSCStub(BaseStub):
    """
    Stub for NRSC high-resolution satellite imagery API.
    
    NRSC provides:
    - High-resolution Cartosat imagery (up to 0.25m)
    - Aerial photography
    - Custom imagery orders
    
    When real API access is obtained, swap this stub with actual
    NRSC API client implementation.
    """
    
    name = "nrsc_stub"
    description = "Mock NRSC high-resolution satellite imagery API"
    
    PRODUCTS = {
        "CARTOSAT-3_PAN": {"resolution": 0.25, "satellite": "Cartosat-3", "sensor": "PAN"},
        "CARTOSAT-3_MX": {"resolution": 1.0, "satellite": "Cartosat-3", "sensor": "MX"},
        "CARTOSAT-2_PAN": {"resolution": 0.65, "satellite": "Cartosat-2", "sensor": "PAN"},
        "CARTOSAT-1_PAN": {"resolution": 2.5, "satellite": "Cartosat-1", "sensor": "PAN"},
        "AERIAL_RGB": {"resolution": 0.10, "satellite": "Aerial", "sensor": "RGB"},
        "AERIAL_MULTISPECTRAL": {"resolution": 0.15, "satellite": "Aerial", "sensor": "MS"},
    }
    
    def __init__(self):
        super().__init__()
        self._scenes: Dict[str, MockNRSCScene] = {}
        self._orders: Dict[str, Dict] = {}
        self._generate_mock_scenes()
    
    def _generate_mock_scenes(self):
        """Generate mock NRSC scenes."""
        base_date = datetime.utcnow() - timedelta(days=180)
        
        for i in range(30):
            acquisition_date = base_date + timedelta(days=random.randint(0, 180))
            product_id = random.choice(list(self.PRODUCTS.keys()))
            product = self.PRODUCTS[product_id]
            
            scene_id = f"NRSC_{product_id}_{acquisition_date.strftime('%Y%m%d')}_{i:04d}"
            
            geometry = {
                "type": "Polygon",
                "coordinates": [[
                    [80.55, 16.45],
                    [80.65, 16.45],
                    [80.65, 16.55],
                    [80.55, 16.55],
                    [80.55, 16.45],
                ]]
            }
            
            order_required = product["resolution"] < 1.0
            
            scene = MockNRSCScene(
                scene_id=scene_id,
                product_id=product_id,
                satellite=product["satellite"],
                sensor=product["sensor"],
                acquisition_date=acquisition_date,
                cloud_cover=round(random.uniform(0, 15), 2),
                resolution=product["resolution"],
                geometry=geometry,
                download_url=f"mock://nrsc/download/{scene_id}" if not order_required else None,
                preview_url=f"mock://nrsc/preview/{scene_id}",
                file_size_mb=round(random.uniform(200, 2000), 2),
                order_required=order_required,
            )
            self._scenes[scene_id] = scene
    
    def is_available(self) -> bool:
        return True
    
    def get_mock_data(self, count: int = 10) -> List[Dict]:
        scenes = list(self._scenes.values())[:count]
        return [self._scene_to_dict(s) for s in scenes]
    
    def _scene_to_dict(self, scene: MockNRSCScene) -> Dict:
        return {
            "scene_id": scene.scene_id,
            "product_id": scene.product_id,
            "satellite": scene.satellite,
            "sensor": scene.sensor,
            "acquisition_date": scene.acquisition_date.isoformat(),
            "cloud_cover": scene.cloud_cover,
            "resolution": scene.resolution,
            "geometry": scene.geometry,
            "download_url": scene.download_url,
            "preview_url": scene.preview_url,
            "file_size_mb": scene.file_size_mb,
            "order_required": scene.order_required,
            "source": "NRSC (Mock)",
        }
    
    async def search_scenes(
        self,
        bbox: List[float] = None,
        start_date: datetime = None,
        end_date: datetime = None,
        product_id: str = None,
        max_resolution: float = None,
        cloud_cover_max: float = 20,
        limit: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search for high-resolution scenes."""
        self.log_stub_call("search_scenes", {
            "bbox": bbox,
            "product_id": product_id,
            "max_resolution": max_resolution,
            "limit": limit,
        })
        
        filtered = list(self._scenes.values())
        
        if start_date:
            filtered = [s for s in filtered if s.acquisition_date >= start_date]
        if end_date:
            filtered = [s for s in filtered if s.acquisition_date <= end_date]
        if product_id:
            filtered = [s for s in filtered if s.product_id == product_id]
        if max_resolution:
            filtered = [s for s in filtered if s.resolution <= max_resolution]
        if cloud_cover_max < 100:
            filtered = [s for s in filtered if s.cloud_cover <= cloud_cover_max]
        
        filtered.sort(key=lambda s: s.acquisition_date, reverse=True)
        
        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        
        return {
            "scenes": [self._scene_to_dict(s) for s in paginated],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    
    async def get_scene(self, scene_id: str) -> Optional[Dict]:
        """Get a specific scene."""
        scene = self._scenes.get(scene_id)
        return self._scene_to_dict(scene) if scene else None
    
    async def download_scene(self, scene_id: str, output_path: str = None) -> StubResponse:
        """Download a scene (or simulate order if required)."""
        self.log_stub_call("download_scene", {"scene_id": scene_id})
        
        scene = self._scenes.get(scene_id)
        if not scene:
            return StubResponse(success=False, data=None, error=f"Scene not found: {scene_id}")
        
        if scene.order_required:
            return StubResponse(
                success=False,
                data={"order_required": True},
                error="This product requires ordering through NRSC portal",
            )
        
        from app.stubs.mock_imagery import MockImageryGenerator
        generator = MockImageryGenerator()
        mock_path = generator.generate_nrsc_image(
            scene_id=scene_id,
            resolution=scene.resolution,
            output_path=output_path,
        )
        
        return StubResponse(
            success=True,
            data={
                "scene_id": scene_id,
                "file_path": mock_path,
                "file_size_mb": scene.file_size_mb,
                "resolution": scene.resolution,
                "source": "NRSC (Mock)",
            },
        )
    
    async def create_order(self, scene_ids: List[str], purpose: str = None) -> StubResponse:
        """Create an order for high-resolution imagery."""
        self.log_stub_call("create_order", {"scene_ids": scene_ids})
        
        order_id = f"NRSC_ORDER_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
        
        self._orders[order_id] = {
            "order_id": order_id,
            "scene_ids": scene_ids,
            "purpose": purpose,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "estimated_delivery": (datetime.utcnow() + timedelta(days=random.randint(3, 7))).isoformat(),
        }
        
        return StubResponse(
            success=True,
            data={
                "order_id": order_id,
                "status": "pending",
                "estimated_delivery_days": random.randint(3, 7),
            },
            message="Order created successfully (Mock)",
        )
    
    async def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get order status."""
        order = self._orders.get(order_id)
        if not order:
            return None
        
        if random.random() > 0.7:
            order["status"] = random.choice(["processing", "approved", "ready_for_download"])
        
        return order
    
    def get_available_products(self) -> List[Dict]:
        """Get list of available NRSC products."""
        return [
            {
                "product_id": pid,
                "resolution": info["resolution"],
                "satellite": info["satellite"],
                "sensor": info["sensor"],
                "order_required": info["resolution"] < 1.0,
            }
            for pid, info in self.PRODUCTS.items()
        ]
