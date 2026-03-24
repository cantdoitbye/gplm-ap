"""
Bhuvan/ISRO API Stub

Provides mock satellite imagery data from ISRO's Bhuvan portal.
This stub simulates Bhuvan API responses for testing.

Real API: https://bhuvan.nrsc.gov.in
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from app.stubs.base import BaseStub, StubResponse


@dataclass
class MockBhuvanScene:
    """Mock Bhuvan satellite scene metadata."""
    scene_id: str
    satellite: str
    sensor: str
    acquisition_date: datetime
    cloud_cover: float
    resolution: float
    path: int
    row: int
    geometry: Dict[str, Any]
    download_url: str
    preview_url: str
    file_size_mb: float


class BhuvanStub(BaseStub):
    """
    Stub for Bhuvan/ISRO satellite imagery API.
    
    Simulates ISRO's satellite imagery services including:
    - Resourcesat-1/2 (LISS-III, LISS-IV, AWiFS)
    - Cartosat-1/2/3
    - RISAT
    
    When real API access is obtained, swap this stub with actual
    Bhuvan API client implementation.
    """
    
    name = "bhuvan_stub"
    description = "Mock Bhuvan/ISRO satellite imagery API"
    
    SATELLITES = {
        "R1": {"name": "Resourcesat-1", "sensors": ["LISS-III", "LISS-IV", "AWiFS"]},
        "R2": {"name": "Resourcesat-2", "sensors": ["LISS-III", "LISS-IV", "AWiFS"]},
        "C1": {"name": "Cartosat-1", "sensors": ["PAN", "PAN-F"]},
        "C2": {"name": "Cartosat-2", "sensors": ["PAN"]},
        "C3": {"name": "Cartosat-3", "sensors": ["PAN", "MX"]},
    }
    
    RESOLUTIONS = {
        "LISS-III": 23.5,
        "LISS-IV": 5.8,
        "AWiFS": 56.0,
        "PAN": 2.5,
        "PAN-F": 1.0,
        "MX": 1.0,
    }
    
    AOI_CENTER = {"lat": 16.5062, "lon": 80.6480}
    
    def __init__(self):
        super().__init__()
        self._scenes: Dict[str, MockBhuvanScene] = {}
        self._generate_mock_scenes()
    
    def _generate_mock_scenes(self):
        """Generate mock Bhuvan satellite scenes."""
        base_date = datetime.utcnow() - timedelta(days=365)
        
        for i in range(50):
            acquisition_date = base_date + timedelta(days=random.randint(0, 365))
            sat_code = random.choice(list(self.SATELLITES.keys()))
            satellite = self.SATELLITES[sat_code]["name"]
            sensor = random.choice(self.SATELLITES[sat_code]["sensors"])
            resolution = self.RESOLUTIONS[sensor]
            
            path = random.randint(90, 110)
            row = random.randint(55, 65)
            
            scene_id = f"{sat_code}_{sensor.replace('-', '')}_{acquisition_date.strftime('%Y%m%d')}_{path:03d}_{row:03d}_{i:04d}"
            
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
            
            scene = MockBhuvanScene(
                scene_id=scene_id,
                satellite=satellite,
                sensor=sensor,
                acquisition_date=acquisition_date,
                cloud_cover=round(random.uniform(0, 30), 2),
                resolution=resolution,
                path=path,
                row=row,
                geometry=geometry,
                download_url=f"mock://bhuvan/download/{scene_id}",
                preview_url=f"mock://bhuvan/preview/{scene_id}",
                file_size_mb=round(random.uniform(100, 500), 2),
            )
            self._scenes[scene_id] = scene
    
    def is_available(self) -> bool:
        """Stub is always available."""
        return True
    
    def get_mock_data(self, count: int = 10) -> List[Dict]:
        """Get mock satellite scenes."""
        scenes = list(self._scenes.values())[:count]
        return [self._scene_to_dict(s) for s in scenes]
    
    def _scene_to_dict(self, scene: MockBhuvanScene) -> Dict:
        """Convert scene to dictionary."""
        return {
            "scene_id": scene.scene_id,
            "satellite": scene.satellite,
            "sensor": scene.sensor,
            "acquisition_date": scene.acquisition_date.isoformat(),
            "cloud_cover": scene.cloud_cover,
            "resolution": scene.resolution,
            "path": scene.path,
            "row": scene.row,
            "geometry": scene.geometry,
            "download_url": scene.download_url,
            "preview_url": scene.preview_url,
            "file_size_mb": scene.file_size_mb,
            "source": "Bhuvan/ISRO",
        }
    
    async def search_scenes(
        self,
        bbox: List[float] = None,
        start_date: datetime = None,
        end_date: datetime = None,
        satellite: str = None,
        sensor: str = None,
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
            satellite: Satellite name filter (e.g., "Cartosat-3")
            sensor: Sensor name filter (e.g., "PAN")
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
            "satellite": satellite,
            "sensor": sensor,
            "cloud_cover_max": cloud_cover_max,
            "limit": limit,
        })
        
        filtered_scenes = list(self._scenes.values())
        
        if start_date:
            filtered_scenes = [s for s in filtered_scenes if s.acquisition_date >= start_date]
        
        if end_date:
            filtered_scenes = [s for s in filtered_scenes if s.acquisition_date <= end_date]
        
        if satellite:
            filtered_scenes = [s for s in filtered_scenes if satellite.lower() in s.satellite.lower()]
        
        if sensor:
            filtered_scenes = [s for s in filtered_scenes if sensor.lower() in s.sensor.lower()]
        
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
        Simulate downloading a scene from Bhuvan.
        
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
        mock_path = generator.generate_bhuvan_image(
            scene_id=scene_id,
            satellite=scene.satellite,
            sensor=scene.sensor,
            resolution=scene.resolution,
            output_path=output_path,
        )
        
        return StubResponse(
            success=True,
            data={
                "scene_id": scene_id,
                "file_path": mock_path,
                "file_size_mb": scene.file_size_mb,
                "download_time_seconds": round(random.uniform(5, 30), 2),
                "source": "Bhuvan/ISRO (Mock)",
            },
            message=f"Mock download completed for {scene_id}",
        )
    
    async def get_preview(self, scene_id: str) -> StubResponse:
        """Get a preview image for a scene."""
        self.log_stub_call("get_preview", {"scene_id": scene_id})
        
        from app.stubs.mock_imagery import MockImageryGenerator
        
        generator = MockImageryGenerator()
        preview_path = generator.generate_preview_image(scene_id, source="bhuvan")
        
        return StubResponse(
            success=True,
            data={"preview_path": preview_path},
        )
    
    def get_latest_scene(self, satellite: str = None, sensor: str = None) -> Optional[Dict]:
        """Get the most recent scene matching criteria."""
        scenes = list(self._scenes.values())
        
        if satellite:
            scenes = [s for s in scenes if satellite.lower() in s.satellite.lower()]
        
        if sensor:
            scenes = [s for s in scenes if sensor.lower() in s.sensor.lower()]
        
        if not scenes:
            return None
        
        scenes.sort(key=lambda s: s.acquisition_date, reverse=True)
        return self._scene_to_dict(scenes[0])
    
    def get_available_satellites(self) -> List[Dict]:
        """Get list of available satellites and sensors."""
        return [
            {
                "code": code,
                "name": info["name"],
                "sensors": info["sensors"],
                "resolutions": {s: self.RESOLUTIONS[s] for s in info["sensors"]},
            }
            for code, info in self.SATELLITES.items()
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about mock data."""
        scenes = list(self._scenes.values())
        
        return {
            "total_scenes": len(scenes),
            "satellites": {sat: len([s for s in scenes if s.satellite == self.SATELLITES[sat]["name"]]) for sat in self.SATELLITES},
            "avg_cloud_cover": round(sum(s.cloud_cover for s in scenes) / len(scenes), 2),
            "date_range": {
                "earliest": min(s.acquisition_date for s in scenes).isoformat(),
                "latest": max(s.acquisition_date for s in scenes).isoformat(),
            },
            "source": "Bhuvan/ISRO (Mock)",
        }
