"""
Meebhoomi Stub

Provides mock cadastral data from Meebhoomi Portal 
(AP Land Records portal).

Real API: https://meebhoomi.ap.gov.in
"""

import random
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from app.stubs.base import BaseStub, StubResponse


@dataclass
class MockCadastralParcel:
    """Mock cadastral parcel data."""
    parcel_id: str
    survey_number: str
    subdivision: str
    village: str
    mandal: str
    district: str
    area_hectares: float
    geometry: Dict[str, Any]
    land_use: str
    irrigation_source: str
    soil_type: str


class MeebhoomiStub(BaseStub):
    """
    Stub for Meebhoomi cadastral portal.
    
    Meebhoomi provides:
    - Cadastral boundaries (village maps)
    - Land parcel geometries
    - FMB (Field Measurement Book) data
    - Adangal records
    
    When real API access is obtained, swap this stub with actual
    Meebhoomi API client implementation.
    """
    
    name = "meebhoomi_stub"
    description = "Mock Meebhoomi cadastral portal"
    
    LAND_USES = ["agricultural", "residential", "commercial", "industrial", "forest", "water", "wasteland"]
    IRRIGATION_SOURCES = ["canal", "borewell", "open_well", "river", "tank", "rainfed"]
    SOIL_TYPES = ["red_soil", "black_soil", "alluvial", "sandy", "loamy", "clay"]
    
    BASE_COORDS = {"lon": 80.6, "lat": 16.5}
    
    def __init__(self):
        super().__init__()
        self._parcels: Dict[str, MockCadastralParcel] = {}
        self._generate_mock_parcels()
    
    def _generate_mock_parcels(self):
        """Generate mock cadastral parcels."""
        districts = ["Guntur", "Krishna", "Visakhapatnam"]
        
        for district_idx, district in enumerate(districts):
            mandals = [f"Mandal_{i + 1}" for i in range(3)]
            
            for mandal_idx, mandal in enumerate(mandals):
                villages = [f"Village_{mandal_idx}_{i + 1}" for i in range(3)]
                
                for village_idx, village in enumerate(villages):
                    base_lon = self.BASE_COORDS["lon"] + (district_idx * 0.1) + (mandal_idx * 0.02)
                    base_lat = self.BASE_COORDS["lat"] + (district_idx * 0.1) + (village_idx * 0.01)
                    
                    for i in range(30):
                        survey_number = f"{random.randint(1, 200)}"
                        subdivision = random.choice(["", "A", "B", "C", "1", "2"])
                        
                        parcel_id = f"{district[:3].upper()}{mandal_idx}{village_idx}{i + 1:04d}"
                        
                        geometry = self._generate_parcel_geometry(base_lon, base_lat, i)
                        area_hectares = round(random.uniform(0.1, 10), 2)
                        
                        parcel = MockCadastralParcel(
                            parcel_id=parcel_id,
                            survey_number=survey_number,
                            subdivision=subdivision,
                            village=village,
                            mandal=mandal,
                            district=district,
                            area_hectares=area_hectares,
                            geometry=geometry,
                            land_use=random.choice(self.LAND_USES),
                            irrigation_source=random.choice(self.IRRIGATION_SOURCES),
                            soil_type=random.choice(self.SOIL_TYPES),
                        )
                        self._parcels[parcel_id] = parcel
    
    def _generate_parcel_geometry(self, base_lon: float, base_lat: float, index: int) -> Dict:
        """Generate mock parcel geometry."""
        offset_x = (index % 10) * 0.005
        offset_y = (index // 10) * 0.005
        
        lon1 = base_lon + offset_x
        lat1 = base_lat + offset_y
        lon2 = lon1 + 0.004
        lat2 = lat1 + 0.004
        
        return {
            "type": "Polygon",
            "coordinates": [[
                [lon1, lat1],
                [lon2, lat1],
                [lon2, lat2],
                [lon1, lat2],
                [lon1, lat1],
            ]]
        }
    
    def is_available(self) -> bool:
        return True
    
    def get_mock_data(self, count: int = 10) -> List[Dict]:
        parcels = list(self._parcels.values())[:count]
        return [self._parcel_to_dict(p) for p in parcels]
    
    def _parcel_to_dict(self, parcel: MockCadastralParcel) -> Dict:
        return {
            "parcel_id": parcel.parcel_id,
            "survey_number": parcel.survey_number,
            "subdivision": parcel.subdivision,
            "location": {
                "village": parcel.village,
                "mandal": parcel.mandal,
                "district": parcel.district,
            },
            "area_hectares": parcel.area_hectares,
            "geometry": parcel.geometry,
            "characteristics": {
                "land_use": parcel.land_use,
                "irrigation_source": parcel.irrigation_source,
                "soil_type": parcel.soil_type,
            },
            "source": "Meebhoomi (Mock)",
        }
    
    async def search_parcels(
        self,
        district: str = None,
        mandal: str = None,
        village: str = None,
        survey_number: str = None,
        land_use: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search cadastral parcels."""
        self.log_stub_call("search_parcels", {
            "district": district,
            "village": village,
            "survey_number": survey_number,
        })
        
        filtered = list(self._parcels.values())
        
        if district:
            filtered = [p for p in filtered if district.lower() in p.district.lower()]
        if mandal:
            filtered = [p for p in filtered if mandal.lower() in p.mandal.lower()]
        if village:
            filtered = [p for p in filtered if village.lower() in p.village.lower()]
        if survey_number:
            filtered = [p for p in filtered if survey_number == p.survey_number]
        if land_use:
            filtered = [p for p in filtered if land_use == p.land_use]
        
        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        
        return {
            "parcels": [self._parcel_to_dict(p) for p in paginated],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    
    async def get_parcel(self, parcel_id: str) -> Optional[Dict]:
        """Get a specific parcel."""
        parcel = self._parcels.get(parcel_id)
        return self._parcel_to_dict(parcel) if parcel else None
    
    async def get_village_map(
        self,
        district: str,
        mandal: str,
        village: str,
        as_geojson: bool = True,
    ) -> StubResponse:
        """Get village cadastral map."""
        self.log_stub_call("get_village_map", {"village": village})
        
        parcels = [
            p for p in self._parcels.values()
            if (district.lower() in p.district.lower() and
                mandal.lower() in p.mandal.lower() and
                village.lower() in p.village.lower())
        ]
        
        if as_geojson:
            features = [
                {
                    "type": "Feature",
                    "geometry": p.geometry,
                    "properties": {
                        "parcel_id": p.parcel_id,
                        "survey_number": p.survey_number,
                        "subdivision": p.subdivision,
                        "area_hectares": p.area_hectares,
                        "land_use": p.land_use,
                    }
                }
                for p in parcels
            ]
            
            geojson = {
                "type": "FeatureCollection",
                "features": features,
                "properties": {
                    "village": village,
                    "mandal": mandal,
                    "district": district,
                    "parcel_count": len(parcels),
                    "source": "Meebhoomi (Mock)",
                }
            }
            
            return StubResponse(success=True, data=geojson)
        
        return StubResponse(success=True, data=[self._parcel_to_dict(p) for p in parcels])
    
    async def get_parcels_by_bbox(
        self,
        bbox: List[float],
        limit: int = 100,
    ) -> StubResponse:
        """Get parcels within bounding box."""
        self.log_stub_call("get_parcels_by_bbox", {"bbox": bbox})
        
        min_lon, min_lat, max_lon, max_lat = bbox
        
        parcels = list(self._parcels.values())[:limit]
        
        features = []
        for parcel in parcels:
            coords = parcel.geometry["coordinates"][0]
            center_lon = sum(c[0] for c in coords) / len(coords)
            center_lat = sum(c[1] for c in coords) / len(coords)
            
            if min_lon <= center_lon <= max_lon and min_lat <= center_lat <= max_lat:
                features.append({
                    "type": "Feature",
                    "geometry": parcel.geometry,
                    "properties": self._parcel_to_dict(parcel),
                })
        
        geojson = {
            "type": "FeatureCollection",
            "features": features,
        }
        
        return StubResponse(success=True, data=geojson)
    
    async def get_summary(self, district: str = None) -> Dict[str, Any]:
        """Get cadastral summary."""
        parcels = list(self._parcels.values())
        
        if district:
            parcels = [p for p in parcels if district.lower() in p.district.lower()]
        
        total_area = sum(p.area_hectares for p in parcels)
        
        return {
            "total_parcels": len(parcels),
            "total_area_hectares": round(total_area, 2),
            "by_land_use": {
                lu: {
                    "count": len([p for p in parcels if p.land_use == lu]),
                    "area": round(sum(p.area_hectares for p in parcels if p.land_use == lu), 2),
                }
                for lu in self.LAND_USES
            },
            "by_soil_type": {
                st: len([p for p in parcels if p.soil_type == st])
                for st in self.SOIL_TYPES
            },
            "source": "Meebhoomi (Mock)",
        }
