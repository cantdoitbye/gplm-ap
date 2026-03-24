"""
Copernicus/Sentinel-2 API Stub

Provides mock satellite imagery data for testing without
requiring Copernicus Data Space credentials.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import uuid

from app.stubs.base import BaseStub, StubResponse


@dataclass
class MockScene:
    """Mock satellite scene metadata."""
    scene_id: str
    satellite: str
    sensor: str
    acquisition_date: datetime
    cloud_cover: float
    resolution: float
    orbit_number: int
    tile_id: str
    geometry: Dict[str, Any]
    download_url: str
    preview_url: str
    file_size_mb: float


class CopernicusStub(BaseStub):
    """
    Stub for Copernicus/Sentinel-2 satellite imagery API.
    
    Provides mock satellite scene metadata and synthetic imagery
    for testing purposes.
    """
    
    name = "copernicus_stub"
    description = "Mock Copernicus/Sentinel-2 satellite imagery API"
    
    SATELLITES = ["S2A", "S2B", "S2C"]
    SENSORS = ["MSI"]
    RESOLUTIONS = [10, 20, 60]
    TILE_IDS = [
        "44PKT", "44PKV", "44PLT", "44PLV",
        "44QKT", "44QKV", "44QLT", "44QLV",
    ]
    
    def __init__(self):
        super().__init__()
        self._scenes: Dict[str, MockScene] = {}
        self._generate_mock_scenes()
    
    def _generate_mock_scenes(self):
        """Generate a set of mock satellite scenes."""
        base_date = datetime.utcnow() - timedelta(days=365)
        
        for i in range(50):
            acquisition_date = base_date + timedelta(days=random.randint(0, 365))
            scene_id = f"S2_{acquisition_date.strftime('%Y%m%d')}_{random.choice(self.TILE_IDS)}_{i:04d}"
            
            geometry = {
                "type": "Polygon",
                "coordinates": [[
                    [80.5, 16.4],
                    [80.7, 16.4],
                    [80.7, 16.6],
                    [80.5, 16.6],
                    [80.5, 16.4],
                ]]
            }
            
            scene = MockScene(
                scene_id=scene_id,
                satellite=random.choice(self.SATELLITES),
                sensor="MSI",
                acquisition_date=acquisition_date,
                cloud_cover=round(random.uniform(0, 50), 2),
                resolution=random.choice(self.RESOLUTIONS),
                orbit_number=random.randint(10000, 50000),
                tile_id=random.choice(self.TILE_IDS),
                geometry=geometry,
                download_url=f"mock://copernicus/download/{scene_id}",
                preview_url=f"mock://copernicus/preview/{scene_id}",
                file_size_mb=round(random.uniform(500, 1500), 2),
            )
            self._scenes[scene_id] = scene
    
    def is_available(self) -> bool:
        """Stub is always available."""
        return True
    
    def get_mock_data(self, count: int = 10) -> List[Dict]:
        """Get mock satellite scenes."""
        scenes = list(self._scenes.values())[:count]
        return [self._scene_to_dict(s) for s in scenes]
    
    def _scene_to_dict(self, scene: MockScene) -> Dict:
        """Convert scene to dictionary."""
        return {
            "scene_id": scene.scene_id,
            "satellite": scene.satellite,
            "sensor": scene.sensor,
            "acquisition_date": scene.acquisition_date.isoformat(),
            "cloud_cover": scene.cloud_cover,
            "resolution": scene.resolution,
            "orbit_number": scene.orbit_number,
            "tile_id": scene.tile_id,
            "geometry": scene.geometry,
            "download_url": scene.download_url,
            "preview_url": scene.preview_url,
            "file_size_mb": scene.file_size_mb,
        }
    
    async def search_scenes(
        self,
        bbox: List[float] = None,
        start_date: datetime = None,
        end_date: datetime = None,
        cloud_cover_max: float = 100,
        limit: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Search for mock satellite scenes.
        
        Args:
            bbox: Bounding box [min_lon, min_lat, max_lon, max_lat]
            start_date: Start date filter
            end_date: End date filter
            cloud_cover_max: Maximum cloud cover percentage
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            Dictionary with scenes and pagination info
        """
        self.log_stub_call("search_scenes", {
            "bbox": bbox,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "cloud_cover_max": cloud_cover_max,
            "limit": limit,
        })
        
        filtered_scenes = list(self._scenes.values())
        
        if start_date:
            filtered_scenes = [s for s in filtered_scenes if s.acquisition_date >= start_date]
        
        if end_date:
            filtered_scenes = [s for s in filtered_scenes if s.acquisition_date <= end_date]
        
        if cloud_cover_max < 100:
            filtered_scenes = [s for s in filtered_scenes if s.cloud_cover <= cloud_cover_max]
        
        filtered_scenes.sort(key=lambda s: s.acquisition_date, reverse=True)
        
        total = len(filtered_scenes)
        paginated = filtered_scenes[offset:offset + limit]
        
        return {
            "scenes": [self._scene_to_dict(s) for s in paginated],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    
    async def get_scene(self, scene_id: str) -> Optional[Dict]:
        """Get a specific scene by ID."""
        self.log_stub_call("get_scene", {"scene_id": scene_id})
        
        scene = self._scenes.get(scene_id)
        if scene:
            return self._scene_to_dict(scene)
        return None
    
    async def download_scene(self, scene_id: str, output_path: str = None) -> StubResponse:
        """
        Simulate downloading a scene.
        
        Returns mock download result with synthetic imagery path.
        """
        self.log_stub_call("download_scene", {"scene_id": scene_id, "output_path": output_path})
        
        scene = self._scenes.get(scene_id)
        if not scene:
            return StubResponse(
                success=False,
                data=None,
                error=f"Scene not found: {scene_id}",
            )
        
        from app.stubs.mock_imagery import MockImageryGenerator
        
        generator = MockImageryGenerator()
        mock_path = generator.generate_sentinel_image(
            scene_id=scene_id,
            width=10980,
            height=10980,
            output_path=output_path,
        )
        
        return StubResponse(
            success=True,
            data={
                "scene_id": scene_id,
                "file_path": mock_path,
                "file_size_mb": scene.file_size_mb,
                "download_time_seconds": round(random.uniform(10, 60), 2),
            },
            message=f"Mock download completed for {scene_id}",
        )
    
    async def get_preview(self, scene_id: str) -> StubResponse:
        """Get a preview image for a scene."""
        self.log_stub_call("get_preview", {"scene_id": scene_id})
        
        from app.stubs.mock_imagery import MockImageryGenerator
        
        generator = MockImageryGenerator()
        preview_path = generator.generate_preview_image(scene_id)
        
        return StubResponse(
            success=True,
            data={"preview_path": preview_path},
        )
    
    def get_latest_scene(self, tile_id: str = None) -> Optional[Dict]:
        """Get the most recent scene for a tile."""
        scenes = list(self._scenes.values())
        
        if tile_id:
            scenes = [s for s in scenes if s.tile_id == tile_id]
        
        if not scenes:
            return None
        
        scenes.sort(key=lambda s: s.acquisition_date, reverse=True)
        return self._scene_to_dict(scenes[0])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about mock data."""
        scenes = list(self._scenes.values())
        
        return {
            "total_scenes": len(scenes),
            "satellites": {sat: len([s for s in scenes if s.satellite == sat]) for sat in self.SATELLITES},
            "avg_cloud_cover": round(sum(s.cloud_cover for s in scenes) / len(scenes), 2),
            "date_range": {
                "earliest": min(s.acquisition_date for s in scenes).isoformat(),
                "latest": max(s.acquisition_date for s in scenes).isoformat(),
            },
        }
