"""
SSLR Stub

Provides mock land ownership records from Andhra Pradesh
Chief Commissioner of Land Administration (SSLR) portal.

Real API: https://sslr.ap.gov.in
"""

import random
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from app.stubs.base import BaseStub, StubResponse


@dataclass
class MockLandRecord:
    """Mock SSLR land record."""
    record_id: str
    survey_number: str
    subdivision: str
    village: str
    mandal: str
    district: str
    owner_name: str
    father_name: str
    land_type: str
    area_acres: float
    classification: str
    registration_date: datetime
    pattadar_passbook: str


class SSLRStub(BaseStub):
    """
    Stub for SSLR land records portal.
    
    SSLR provides:
    - Land ownership records (Pahani/ROR)
    - Survey boundaries
    - Pattadar passbook data
    - Land classification
    
    When real API access is obtained, swap this stub with actual
    SSLR API client implementation.
    """
    
    name = "sslr_stub"
    description = "Mock SSLR land records portal"
    
    LAND_TYPES = ["wetland", "dryland", "garden", "poramboke"]
    CLASSIFICATIONS = ["agricultural", "non_agricultural", "government", "assigned"]
    DISTRICTS = ["Guntur", "Krishna", "Visakhapatnam", "West Godavari", "East Godavari"]
    
    VILLAGES_BY_DISTRICT = {
        "Guntur": ["Tadepalle", "Mangalagiri", "Tenali", "Bapatla", "Ponnur"],
        "Krishna": ["Vijayawada", "Machilipatnam", "Gudivada", "Nuzvid", "Tiruvuru"],
        "Visakhapatnam": ["Anakapalle", "Bheemunipatnam", "Narsipatnam", "Yelamanchili"],
        "West Godavari": ["Bhimavaram", "Eluru", "Tadepalligudem", "Narasapuram"],
        "East Godavari": ["Kakinada", "Rajahmundry", "Amalapuram", "Peddapuram"],
    }
    
    def __init__(self):
        super().__init__()
        self._records: Dict[str, MockLandRecord] = {}
        self._generate_mock_records()
    
    def _generate_mock_records(self):
        """Generate mock land records."""
        for district, villages in self.VILLAGES_BY_DISTRICT.items():
            district_code = district[:3].upper()
            
            for village in villages:
                village_code = village[:4].upper()
                mandal = f"{village} Mandal"
                
                for i in range(50):
                    survey_number = f"{random.randint(1, 999)}/{random.choice(['A', 'B', 'C', ''])}"
                    subdivision = random.choice(["AA", "AB", "BA", "BB", ""])
                    
                    record_id = f"{district_code}{village_code}{i + 1:05d}"
                    area_acres = round(random.uniform(0.5, 50), 2)
                    
                    record = MockLandRecord(
                        record_id=record_id,
                        survey_number=survey_number.rstrip("/"),
                        subdivision=subdivision,
                        village=village,
                        mandal=mandal,
                        district=district,
                        owner_name=f"Farmer {random.randint(1, 5000)}",
                        father_name=f"Father {random.randint(1, 5000)}",
                        land_type=random.choice(self.LAND_TYPES),
                        area_acres=area_acres,
                        classification=random.choice(self.CLASSIFICATIONS),
                        registration_date=datetime(
                            random.randint(2010, 2024),
                            random.randint(1, 12),
                            random.randint(1, 28)
                        ),
                        pattadar_passbook=f"PPB/{district_code}/{random.randint(100000, 999999)}",
                    )
                    self._records[record_id] = record
    
    def is_available(self) -> bool:
        return True
    
    def get_mock_data(self, count: int = 10) -> List[Dict]:
        records = list(self._records.values())[:count]
        return [self._record_to_dict(r) for r in records]
    
    def _record_to_dict(self, record: MockLandRecord) -> Dict:
        return {
            "record_id": record.record_id,
            "survey_number": record.survey_number,
            "subdivision": record.subdivision,
            "location": {
                "village": record.village,
                "mandal": record.mandal,
                "district": record.district,
            },
            "owner": {
                "name": record.owner_name,
                "father_name": record.father_name,
            },
            "land": {
                "type": record.land_type,
                "area_acres": record.area_acres,
                "classification": record.classification,
            },
            "registration_date": record.registration_date.isoformat(),
            "pattadar_passbook": record.pattadar_passbook,
            "source": "SSLR (Mock)",
        }
    
    async def search_records(
        self,
        district: str = None,
        mandal: str = None,
        village: str = None,
        survey_number: str = None,
        owner_name: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search land records."""
        self.log_stub_call("search_records", {
            "district": district,
            "village": village,
            "survey_number": survey_number,
        })
        
        filtered = list(self._records.values())
        
        if district:
            filtered = [r for r in filtered if district.lower() in r.district.lower()]
        if mandal:
            filtered = [r for r in filtered if mandal.lower() in r.mandal.lower()]
        if village:
            filtered = [r for r in filtered if village.lower() in r.village.lower()]
        if survey_number:
            filtered = [r for r in filtered if survey_number in r.survey_number]
        if owner_name:
            filtered = [r for r in filtered if owner_name.lower() in r.owner_name.lower()]
        
        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        
        return {
            "records": [self._record_to_dict(r) for r in paginated],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    
    async def get_record(self, record_id: str) -> Optional[Dict]:
        """Get a specific land record."""
        record = self._records.get(record_id)
        return self._record_to_dict(record) if record else None
    
    async def get_records_by_survey(
        self,
        district: str,
        mandal: str,
        village: str,
        survey_number: str,
    ) -> List[Dict]:
        """Get all records for a survey number."""
        results = [
            self._record_to_dict(r)
            for r in self._records.values()
            if (district.lower() in r.district.lower() and
                mandal.lower() in r.mandal.lower() and
                village.lower() in r.village.lower() and
                survey_number in r.survey_number)
        ]
        return results
    
    async def get_villages(self, district: str) -> List[str]:
        """Get villages in a district."""
        return self.VILLAGES_BY_DISTRICT.get(district, [])
    
    async def get_summary(self, district: str = None) -> Dict[str, Any]:
        """Get land records summary."""
        records = list(self._records.values())
        
        if district:
            records = [r for r in records if district.lower() in r.district.lower()]
        
        total_area = sum(r.area_acres for r in records)
        
        return {
            "total_records": len(records),
            "total_area_acres": round(total_area, 2),
            "by_land_type": {
                ltype: {
                    "count": len([r for r in records if r.land_type == ltype]),
                    "area": round(sum(r.area_acres for r in records if r.land_type == ltype), 2),
                }
                for ltype in self.LAND_TYPES
            },
            "by_classification": {
                cls: len([r for r in records if r.classification == cls])
                for cls in self.CLASSIFICATIONS
            },
            "source": "SSLR (Mock)",
        }
    
    def get_districts(self) -> List[str]:
        """Get list of districts."""
        return self.DISTRICTS
