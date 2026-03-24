"""
Mock Data Generator for AIKOSH-5

Generates synthetic property records, cadastral boundaries,
municipalities, and other mock data for development and testing.
"""

import os
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import numpy as np
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class MockDataGenerator:
    """
    Generates mock data for AIKOSH-5 development.
    
    Creates:
    - Municipalities with boundaries
    - Property parcels with buildings
    - Survey numbers and ownership data
    - Historical changes for testing change detection
    """
    
    PROPERTY_TYPES = [
        "residential",
        "commercial",
        "industrial",
        "agricultural",
        "institutional",
        "vacant",
    ]
    
    LAND_USES = [
        "residential",
        "commercial",
        "industrial",
        "agricultural",
        "recreational",
        "institutional",
        "transportation",
        "water_body",
        "vacant",
    ]
    
    STREETS = [
        "MG Road", "Station Road", "Market Street", "Temple Street",
        "School Road", "Hospital Road", "Park Avenue", "Lake View Road",
        "Industrial Area", "Business Park", "Tech Park", "Green Valley",
    ]
    
    AREAS = [
        "Kukatpally", "Secunderabad", "Banjara Hills", "Jubilee Hills",
        "Madhapur", "Gachibowli", "Hitech City", "Kondapur",
    ]
    
    def __init__(
        self,
        seed: int = None,
        output_dir: str = "data/mock",
    ):
        self.seed = seed or settings.MOCK_DATA_SEED
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        random.seed(self.seed)
        np.random.seed(self.seed)
    
    def generate_municipalities(
        self,
        center_lat: float,
        center_lon: float,
        count: int = 3,
        spread_km: float = 5.0,
    ) -> gpd.GeoDataFrame:
        """
        Generate mock municipalities.
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            count: Number of municipalities
            spread_km: Spread distance in kilometers
        
        Returns:
            GeoDataFrame of municipalities
        """
        municipalities = []
        
        for i in range(count):
            offset_lat = (random.random() - 0.5) * spread_km / 111
            offset_lon = (random.random() - 0.5) * spread_km / 111
            
            lat = center_lat + offset_lat
            lon = center_lon + offset_lon
            
            size = random.uniform(0.01, 0.03)
            
            coords = [
                (lon - size, lat - size),
                (lon + size, lat - size),
                (lon + size, lat + size),
                (lon - size, lat + size),
                (lon - size, lat - size),
            ]
            
            polygon = Polygon(coords)
            
            municipality = {
                "id": i + 1,
                "name": f"Municipality {chr(65 + i)}",
                "code": f"ULB{i+1:03d}",
                "district": "Guntur",
                "state": "Andhra Pradesh",
                "geometry": polygon,
                "area_sqkm": polygon.area * 111 * 111,
                "population": random.randint(50000, 200000),
            }
            municipalities.append(municipality)
        
        gdf = gpd.GeoDataFrame(municipalities, crs="EPSG:4326")
        return gdf
    
    def generate_properties(
        self,
        municipality_gdf: gpd.GeoDataFrame,
        properties_per_municipality: int = 100,
    ) -> gpd.GeoDataFrame:
        """
        Generate mock property parcels within municipalities.
        
        Args:
            municipality_gdf: GeoDataFrame of municipalities
            properties_per_municipality: Properties to generate per municipality
        
        Returns:
            GeoDataFrame of properties
        """
        properties = []
        property_id = 1
        
        for _, muni in municipality_gdf.iterrows():
            muni_geom = muni["geometry"]
            minx, miny, maxx, maxy = muni_geom.bounds
            
            for i in range(properties_per_municipality):
                lat = miny + random.random() * (maxy - miny)
                lon = minx + random.random() * (maxx - minx)
                
                point = Point(lon, lat)
                
                if not muni_geom.contains(point):
                    continue
                
                size = random.uniform(0.0002, 0.001)
                aspect = random.uniform(0.5, 2.0)
                
                coords = [
                    (lon - size/2, lat - size*aspect/2),
                    (lon + size/2, lat - size*aspect/2),
                    (lon + size/2, lat + size*aspect/2),
                    (lon - size/2, lat + size*aspect/2),
                    (lon - size/2, lat - size*aspect/2),
                ]
                
                parcel = Polygon(coords)
                
                area_sqm = parcel.area * 111320 * 111320
                
                survey_num = f"{random.randint(1, 999)}/{random.choice(['A', 'B', 'C', ''])}"
                
                property_type = random.choice(self.PROPERTY_TYPES)
                
                if property_type == "residential":
                    built_area = area_sqm * random.uniform(0.3, 0.8)
                elif property_type == "commercial":
                    built_area = area_sqm * random.uniform(0.5, 1.0)
                elif property_type == "vacant":
                    built_area = 0
                else:
                    built_area = area_sqm * random.uniform(0.2, 0.6)
                
                prop = {
                    "id": property_id,
                    "property_id": f"PROP{property_id:06d}",
                    "municipality_id": muni["id"],
                    "survey_number": survey_num,
                    "subdivision": f"{random.randint(1, 99)}",
                    "owner_name": self._generate_name(),
                    "property_type": property_type,
                    "land_use": random.choice(self.LAND_USES),
                    "area_sqm": round(area_sqm, 2),
                    "built_area_sqm": round(built_area, 2),
                    "address": self._generate_address(),
                    "is_verified": random.random() > 0.3,
                    "last_survey_date": self._generate_date(),
                    "geometry": parcel,
                    "centroid": point,
                }
                properties.append(prop)
                property_id += 1
        
        gdf = gpd.GeoDataFrame(properties, crs="EPSG:4326")
        return gdf
    
    def generate_change_history(
        self,
        properties_gdf: gpd.GeoDataFrame,
        changes_per_property: float = 0.2,
    ) -> List[Dict[str, Any]]:
        """
        Generate mock change history for properties.
        
        Args:
            properties_gdf: GeoDataFrame of properties
            changes_per_property: Average changes per property
        
        Returns:
            List of change records
        """
        changes = []
        change_id = 1
        
        for _, prop in properties_gdf.iterrows():
            if random.random() > changes_per_property:
                continue
            
            num_changes = random.randint(1, 3)
            
            for _ in range(num_changes):
                change_date = self._generate_date()
                change_type = random.choice([
                    "construction",
                    "expansion",
                    "demolition",
                    "land_use_change",
                    "ownership_transfer",
                ])
                
                change = {
                    "id": change_id,
                    "property_id": prop["id"],
                    "change_type": change_type,
                    "change_date": change_date.isoformat(),
                    "previous_state": {
                        "built_area_sqm": prop["built_area_sqm"] * random.uniform(0.5, 0.9),
                        "land_use": random.choice(self.LAND_USES),
                    },
                    "current_state": {
                        "built_area_sqm": prop["built_area_sqm"],
                        "land_use": prop["land_use"],
                    },
                    "detected_by": random.choice(["satellite", "survey", "citizen_report"]),
                    "verified": random.random() > 0.3,
                }
                changes.append(change)
                change_id += 1
        
        return changes
    
    def generate_alerts(
        self,
        changes: List[Dict[str, Any]],
        alert_ratio: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Generate mock alerts from changes.
        """
        alerts = []
        
        for i, change in enumerate(changes):
            if random.random() > alert_ratio:
                continue
            
            severity = random.choice(["critical", "high", "medium", "low"])
            
            alert = {
                "id": i + 1,
                "change_id": change["id"],
                "property_id": change["property_id"],
                "title": f"{change['change_type'].replace('_', ' ').title()} Detected",
                "description": f"Detected {change['change_type']} on property {change['property_id']}",
                "severity": severity,
                "status": random.choice(["new", "acknowledged", "resolved", "dismissed"]),
                "created_at": change["change_date"],
            }
            alerts.append(alert)
        
        return alerts
    
    def generate_users(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate mock users."""
        roles = ["admin", "officer", "surveyor", "viewer"]
        users = []
        
        for i in range(count):
            user = {
                "id": i + 1,
                "username": f"user{i+1}",
                "email": f"user{i+1}@aikosh5.gov.in",
                "full_name": self._generate_name(),
                "department": random.choice(["MA&UD", "CDMA", "DTCP", "SSLR", "APSAC"]),
                "role": random.choice(roles),
                "is_active": random.random() > 0.1,
            }
            users.append(user)
        
        return users
    
    def _generate_name(self) -> str:
        """Generate a random Indian name."""
        first_names = [
            "Rajesh", "Suresh", "Venkat", "Krishna", "Rama",
            "Lakshmi", "Sridevi", "Padma", "Lakshman", "Nagaraju",
            "Prasad", "Rao", "Kumar", "Reddy", "Naidu",
        ]
        last_names = [
            "Kumar", "Reddy", "Naidu", "Rao", "Sharma",
            "Prasad", "Murthy", "Raju", "Babu", "Devi",
        ]
        
        return f"{random.choice(first_names)} {random.choice(last_names)}"
    
    def _generate_address(self) -> str:
        """Generate a random address."""
        street = random.choice(self.STREETS)
        area = random.choice(self.AREAS)
        number = random.randint(1, 999)
        
        return f"{number}, {street}, {area}"
    
    def _generate_date(
        self,
        start_year: int = 2020,
        end_year: int = 2024,
    ) -> datetime:
        """Generate a random date."""
        start = datetime(start_year, 1, 1)
        end = datetime(end_year, 12, 31)
        
        delta = end - start
        random_days = random.randint(0, delta.days)
        
        return start + timedelta(days=random_days)
    
    def generate_all(
        self,
        center_lat: float = None,
        center_lon: float = None,
        municipalities_count: int = None,
        properties_per_municipality: int = None,
    ) -> Dict[str, Any]:
        """
        Generate all mock data and save to files.
        
        Returns:
            Dictionary with file paths
        """
        center_lat = center_lat or settings.AOI_CENTER_LAT
        center_lon = center_lon or settings.AOI_CENTER_LON
        municipalities_count = municipalities_count or settings.MOCK_MUNICIPALITIES_COUNT
        properties_per_municipality = properties_per_municipality or (settings.MOCK_PROPERTIES_COUNT // municipalities_count)
        
        logger.info(f"Generating mock data for {municipalities_count} municipalities")
        
        municipalities = self.generate_municipalities(
            center_lat, center_lon, municipalities_count
        )
        
        properties = self.generate_properties(
            municipalities, properties_per_municipality
        )
        
        changes = self.generate_change_history(properties)
        
        alerts = self.generate_alerts(changes)
        
        users = self.generate_users()
        
        file_paths = {}
        
        municipalities_path = os.path.join(self.output_dir, "municipalities.geojson")
        municipalities.to_file(municipalities_path, driver="GeoJSON")
        file_paths["municipalities"] = municipalities_path
        
        properties_path = os.path.join(self.output_dir, "properties.geojson")
        properties.to_file(properties_path, driver="GeoJSON")
        file_paths["properties"] = properties_path
        
        changes_path = os.path.join(self.output_dir, "changes.json")
        with open(changes_path, "w") as f:
            json.dump(changes, f, indent=2, default=str)
        file_paths["changes"] = changes_path
        
        alerts_path = os.path.join(self.output_dir, "alerts.json")
        with open(alerts_path, "w") as f:
            json.dump(alerts, f, indent=2, default=str)
        file_paths["alerts"] = alerts_path
        
        users_path = os.path.join(self.output_dir, "users.json")
        with open(users_path, "w") as f:
            json.dump(users, f, indent=2)
        file_paths["users"] = users_path
        
        summary = {
            "municipalities": len(municipalities),
            "properties": len(properties),
            "changes": len(changes),
            "alerts": len(alerts),
            "users": len(users),
        }
        
        summary_path = os.path.join(self.output_dir, "summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        file_paths["summary"] = summary_path
        
        logger.info(f"Generated mock data: {summary}")
        
        return {
            "file_paths": file_paths,
            "summary": summary,
        }


def generate_mock_data(
    output_dir: str = "data/mock",
    properties_count: int = 1000,
    municipalities_count: int = 3,
) -> Dict[str, Any]:
    """
    Convenience function to generate all mock data.
    """
    generator = MockDataGenerator(output_dir=output_dir)
    return generator.generate_all(
        municipalities_count=municipalities_count,
        properties_per_municipality=properties_count // municipalities_count,
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate mock data for AIKOSH-5")
    parser.add_argument("--output", default="data/mock", help="Output directory")
    parser.add_argument("--properties", type=int, default=1000, help="Number of properties")
    parser.add_argument("--municipalities", type=int, default=3, help="Number of municipalities")
    
    args = parser.parse_args()
    
    result = generate_mock_data(
        output_dir=args.output,
        properties_count=args.properties,
        municipalities_count=args.municipalities,
    )
    
    print(f"Generated data: {result['summary']}")
    for key, path in result['file_paths'].items():
        print(f"  {key}: {path}")
