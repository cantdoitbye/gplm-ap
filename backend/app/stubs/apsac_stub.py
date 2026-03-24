"""
APSAC Portal Stub

Provides mock GIS layers from Andhra Pradesh State Spatial 
Data Infrastructure (APSAC) portal.

Real API: https://apsac.ap.gov.in
"""

import random
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from app.stubs.base import BaseStub, StubResponse


@dataclass
class MockGISLayer:
    """Mock GIS layer metadata."""
    layer_id: str
    name: str
    category: str
    geometry_type: str
    srid: int
    attributes: List[str]
    feature_count: int
    bbox: List[float]
    wms_url: str
    wfs_url: str


class APSACStub(BaseStub):
    """
    Stub for APSAC Portal GIS layers API.
    
    APSAC provides:
    - Administrative boundaries (districts, mandals, villages)
    - Infrastructure layers (roads, railways, water bodies)
    - Land use/land cover
    - Soil maps
    - Water resources
    
    When real API access is obtained, swap this stub with actual
    APSAC API client implementation.
    """
    
    name = "apsac_stub"
    description = "Mock APSAC Portal GIS layers API"
    
    LAYER_CATEGORIES = {
        "administrative": ["districts", "mandals", "villages", "municipal_wards"],
        "infrastructure": ["roads", "railways", "airports", "ports"],
        "water": ["rivers", "canals", "lakes", "reservoirs", "drainage"],
        "land_use": ["built_up", "agricultural", "forest", "wasteland", "water_bodies"],
        "soil": ["soil_types", "soil_depth", "erosion"],
        "environment": ["forest_cover", "wetlands", "coastal_zones"],
    }
    
    GUNTUR_BBOX = [80.4, 16.3, 80.8, 16.7]
    
    def __init__(self):
        super().__init__()
        self._layers: Dict[str, MockGISLayer] = {}
        self._generate_mock_layers()
    
    def _generate_mock_layers(self):
        """Generate mock GIS layers."""
        for category, layers in self.LAYER_CATEGORIES.items():
            for layer_name in layers:
                layer_id = f"apsac_{category}_{layer_name}"
                
                geometry_type = self._get_geometry_type(category, layer_name)
                attributes = self._get_attributes(category, layer_name)
                
                layer = MockGISLayer(
                    layer_id=layer_id,
                    name=f"{layer_name.replace('_', ' ').title()} - {category.title()}",
                    category=category,
                    geometry_type=geometry_type,
                    srid=4326,
                    attributes=attributes,
                    feature_count=random.randint(50, 5000),
                    bbox=self.GUNTUR_BBOX,
                    wms_url=f"mock://apsac/wms/{layer_id}",
                    wfs_url=f"mock://apsac/wfs/{layer_id}",
                )
                self._layers[layer_id] = layer
    
    def _get_geometry_type(self, category: str, layer_name: str) -> str:
        """Determine geometry type for layer."""
        point_layers = ["airports", "ports"]
        line_layers = ["roads", "railways", "rivers", "canals", "drainage"]
        
        if any(p in layer_name for p in point_layers):
            return "Point"
        if any(l in layer_name for l in line_layers):
            return "LineString"
        return "Polygon"
    
    def _get_attributes(self, category: str, layer_name: str) -> List[str]:
        """Get attributes for layer."""
        common = ["id", "name", "area_sqkm", "created_date"]
        
        if category == "administrative":
            return common + ["code", "population", "households"]
        if category == "infrastructure":
            return common + ["type", "length_km", "status"]
        if category == "water":
            return common + ["type", "capacity_mcm", "status"]
        if category == "land_use":
            return common + ["class", "subclass", "change_type"]
        if category == "soil":
            return common + ["soil_type", "depth_cm", "fertility"]
        
        return common
    
    def is_available(self) -> bool:
        return True
    
    def get_mock_data(self, count: int = 10) -> List[Dict]:
        layers = list(self._layers.values())[:count]
        return [self._layer_to_dict(l) for l in layers]
    
    def _layer_to_dict(self, layer: MockGISLayer) -> Dict:
        return {
            "layer_id": layer.layer_id,
            "name": layer.name,
            "category": layer.category,
            "geometry_type": layer.geometry_type,
            "srid": layer.srid,
            "attributes": layer.attributes,
            "feature_count": layer.feature_count,
            "bbox": layer.bbox,
            "wms_url": layer.wms_url,
            "wfs_url": layer.wfs_url,
            "source": "APSAC (Mock)",
        }
    
    async def list_layers(
        self,
        category: str = None,
        geometry_type: str = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List available GIS layers."""
        self.log_stub_call("list_layers", {"category": category})
        
        layers = list(self._layers.values())
        
        if category:
            layers = [l for l in layers if l.category == category]
        if geometry_type:
            layers = [l for l in layers if l.geometry_type == geometry_type]
        
        return {
            "layers": [self._layer_to_dict(l) for l in layers[:limit]],
            "total": len(layers),
        }
    
    async def get_layer(self, layer_id: str) -> Optional[Dict]:
        """Get layer metadata."""
        layer = self._layers.get(layer_id)
        return self._layer_to_dict(layer) if layer else None
    
    async def get_features(
        self,
        layer_id: str,
        bbox: List[float] = None,
        limit: int = 100,
        as_geojson: bool = True,
    ) -> StubResponse:
        """Get features from a layer."""
        self.log_stub_call("get_features", {"layer_id": layer_id, "bbox": bbox})
        
        layer = self._layers.get(layer_id)
        if not layer:
            return StubResponse(success=False, data=None, error=f"Layer not found: {layer_id}")
        
        features = self._generate_mock_features(layer, bbox, limit)
        
        if as_geojson:
            geojson = {
                "type": "FeatureCollection",
                "features": features,
                "properties": {
                    "layer_id": layer_id,
                    "source": "APSAC (Mock)",
                    "feature_count": len(features),
                }
            }
            return StubResponse(success=True, data=geojson)
        
        return StubResponse(success=True, data=features)
    
    def _generate_mock_features(
        self,
        layer: MockGISLayer,
        bbox: List[float],
        limit: int,
    ) -> List[Dict]:
        """Generate mock GeoJSON features."""
        features = []
        bbox = bbox or layer.bbox
        
        for i in range(min(limit, layer.feature_count)):
            coords = self._generate_coordinates(layer.geometry_type, bbox)
            
            properties = {"id": i + 1, "name": f"{layer.layer_id}_{i + 1}"}
            for attr in layer.attributes:
                if attr == "area_sqkm":
                    properties[attr] = round(random.uniform(0.1, 100), 2)
                elif attr == "population":
                    properties[attr] = random.randint(100, 100000)
                elif attr == "code":
                    properties[attr] = f"CODE{i + 1:04d}"
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": layer.geometry_type,
                    "coordinates": coords,
                },
                "properties": properties,
            }
            features.append(feature)
        
        return features
    
    def _generate_coordinates(self, geom_type: str, bbox: List[float]) -> Any:
        """Generate mock coordinates."""
        min_lon, min_lat, max_lon, max_lat = bbox
        
        if geom_type == "Point":
            return [
                random.uniform(min_lon, max_lon),
                random.uniform(min_lat, max_lat),
            ]
        
        if geom_type == "LineString":
            return [
                [random.uniform(min_lon, max_lon), random.uniform(min_lat, max_lat)]
                for _ in range(random.randint(3, 10))
            ]
        
        lon1 = random.uniform(min_lon, (min_lon + max_lon) / 2)
        lat1 = random.uniform(min_lat, (min_lat + max_lat) / 2)
        lon2 = random.uniform((min_lon + max_lon) / 2, max_lon)
        lat2 = random.uniform((min_lat + max_lat) / 2, max_lat)
        
        return [[
            [lon1, lat1],
            [lon2, lat1],
            [lon2, lat2],
            [lon1, lat2],
            [lon1, lat1],
        ]]
    
    async def get_wms_tile(self, layer_id: str, z: int, x: int, y: int) -> StubResponse:
        """Get WMS tile (returns placeholder)."""
        self.log_stub_call("get_wms_tile", {"layer_id": layer_id, "z": z, "x": x, "y": y})
        
        return StubResponse(
            success=True,
            data={"tile_url": f"mock://apsac/tiles/{layer_id}/{z}/{x}/{y}.png"},
        )
    
    def get_categories(self) -> List[Dict]:
        """Get available layer categories."""
        return [
            {
                "category": cat,
                "layer_count": len(layers),
                "layers": layers,
            }
            for cat, layers in self.LAYER_CATEGORIES.items()
        ]
