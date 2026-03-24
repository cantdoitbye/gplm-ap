"""
CDMA Database Stub

Provides mock municipal property records from Commissioner &
Director of Municipal Administration (CDMA) database.

Real API: https://cdma.ap.gov.in
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from app.stubs.base import BaseStub, StubResponse


@dataclass
class MockPropertyRecord:
    """Mock CDMA property record."""
    property_id: str
    assessment_number: str
    owner_name: str
    door_number: str
    street: str
    ward: str
    municipality: str
    property_type: str
    usage: str
    area_sqft: float
    built_area_sqft: float
    tax_amount: float
    tax_due: float
    last_payment_date: datetime
    status: str


class CDMAStub(BaseStub):
    """
    Stub for CDMA property records database.
    
    CDMA provides:
    - Property tax records
    - Building permissions
    - Water/sewerage connections
    - Trade licenses
    
    When real API access is obtained, swap this stub with actual
    CDMA API client implementation.
    """
    
    name = "cdma_stub"
    description = "Mock CDMA property records database"
    
    PROPERTY_TYPES = ["residential", "commercial", "industrial", "institutional", "vacant"]
    USAGE_TYPES = ["self_occupied", "rented", "vacant", "under_construction"]
    MUNICIPALITIES = [
        "Guntur Municipal Corporation",
        "Vijayawada Municipal Corporation",
        "Vizag Municipal Corporation",
    ]
    
    def __init__(self):
        super().__init__()
        self._properties: Dict[str, MockPropertyRecord] = {}
        self._generate_mock_properties()
    
    def _generate_mock_properties(self):
        """Generate mock property records."""
        for muni in self.MUNICIPALITIES:
            muni_code = muni.split()[0][:3].upper()
            
            for i in range(200):
                property_id = f"{muni_code}PROP{i + 1:06d}"
                assessment_number = f"{muni_code}/ASS/{random.randint(10000, 99999)}"
                
                ward = f"Ward-{random.randint(1, 50)}"
                street = f"{random.choice(['Main', 'Cross', 'Ring', 'Station'])} Road, {random.randint(1, 100)}"
                door_number = f"{random.randint(1, 500)}{'ABCDEFG'[random.randint(0, 6)]}"
                
                area_sqft = random.uniform(500, 10000)
                built_area_sqft = area_sqft * random.uniform(0.3, 0.9)
                tax_amount = round(built_area_sqft * random.uniform(2, 10), 2)
                tax_due = round(tax_amount * random.uniform(0, 0.5), 2) if random.random() > 0.3 else 0
                
                last_payment = datetime.utcnow() - timedelta(days=random.randint(0, 365))
                
                record = MockPropertyRecord(
                    property_id=property_id,
                    assessment_number=assessment_number,
                    owner_name=f"Owner {random.randint(1, 10000)}",
                    door_number=door_number,
                    street=street,
                    ward=ward,
                    municipality=muni,
                    property_type=random.choice(self.PROPERTY_TYPES),
                    usage=random.choice(self.USAGE_TYPES),
                    area_sqft=round(area_sqft, 2),
                    built_area_sqft=round(built_area_sqft, 2),
                    tax_amount=tax_amount,
                    tax_due=tax_due,
                    last_payment_date=last_payment,
                    status=random.choice(["active", "inactive", "disputed"]),
                )
                self._properties[property_id] = record
    
    def is_available(self) -> bool:
        return True
    
    def get_mock_data(self, count: int = 10) -> List[Dict]:
        properties = list(self._properties.values())[:count]
        return [self._record_to_dict(p) for p in properties]
    
    def _record_to_dict(self, record: MockPropertyRecord) -> Dict:
        return {
            "property_id": record.property_id,
            "assessment_number": record.assessment_number,
            "owner_name": record.owner_name,
            "address": {
                "door_number": record.door_number,
                "street": record.street,
                "ward": record.ward,
                "municipality": record.municipality,
            },
            "property_type": record.property_type,
            "usage": record.usage,
            "area_sqft": record.area_sqft,
            "built_area_sqft": record.built_area_sqft,
            "tax": {
                "annual_amount": record.tax_amount,
                "due_amount": record.tax_due,
                "last_payment_date": record.last_payment_date.isoformat(),
            },
            "status": record.status,
            "source": "CDMA (Mock)",
        }
    
    async def search_properties(
        self,
        municipality: str = None,
        ward: str = None,
        property_type: str = None,
        owner_name: str = None,
        assessment_number: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search property records."""
        self.log_stub_call("search_properties", {
            "municipality": municipality,
            "ward": ward,
            "property_type": property_type,
        })
        
        filtered = list(self._properties.values())
        
        if municipality:
            filtered = [p for p in filtered if municipality.lower() in p.municipality.lower()]
        if ward:
            filtered = [p for p in filtered if ward.lower() in p.ward.lower()]
        if property_type:
            filtered = [p for p in filtered if p.property_type == property_type]
        if owner_name:
            filtered = [p for p in filtered if owner_name.lower() in p.owner_name.lower()]
        if assessment_number:
            filtered = [p for p in filtered if assessment_number in p.assessment_number]
        
        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        
        return {
            "properties": [self._record_to_dict(p) for p in paginated],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    
    async def get_property(self, property_id: str) -> Optional[Dict]:
        """Get a specific property record."""
        record = self._properties.get(property_id)
        return self._record_to_dict(record) if record else None
    
    async def get_property_by_assessment(self, assessment_number: str) -> Optional[Dict]:
        """Get property by assessment number."""
        for record in self._properties.values():
            if record.assessment_number == assessment_number:
                return self._record_to_dict(record)
        return None
    
    async def get_tax_summary(self, municipality: str = None) -> Dict[str, Any]:
        """Get tax collection summary."""
        properties = list(self._properties.values())
        
        if municipality:
            properties = [p for p in properties if municipality.lower() in p.municipality.lower()]
        
        total_tax = sum(p.tax_amount for p in properties)
        total_due = sum(p.tax_due for p in properties)
        
        return {
            "total_properties": len(properties),
            "total_annual_tax": round(total_tax, 2),
            "total_tax_due": round(total_due, 2),
            "collection_rate": round((total_tax - total_due) / total_tax * 100, 2) if total_tax > 0 else 0,
            "by_type": {
                ptype: {
                    "count": len([p for p in properties if p.property_type == ptype]),
                    "total_tax": round(sum(p.tax_amount for p in properties if p.property_type == ptype), 2),
                }
                for ptype in self.PROPERTY_TYPES
            },
            "source": "CDMA (Mock)",
        }
    
    async def get_properties_by_location(
        self,
        bbox: List[float] = None,
        limit: int = 100,
    ) -> StubResponse:
        """Get properties within a bounding box."""
        self.log_stub_call("get_properties_by_location", {"bbox": bbox})
        
        properties = list(self._properties.values())[:limit]
        
        features = []
        for i, prop in enumerate(properties):
            lon = 80.5 + (i / len(properties)) * 0.3
            lat = 16.4 + random.uniform(0, 0.2)
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
                "properties": self._record_to_dict(prop),
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features,
        }
        
        return StubResponse(success=True, data=geojson)
    
    def get_municipalities(self) -> List[str]:
        """Get list of municipalities."""
        return self.MUNICIPALITIES
