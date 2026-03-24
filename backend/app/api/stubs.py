"""
Stub Testing API

Endpoints to test and verify all government API stubs.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any, List

router = APIRouter(prefix="/stubs", tags=["stubs"])


@router.get("/")
async def list_stubs() -> Dict[str, Any]:
    """List all available stubs."""
    from app.stubs.factory import StubFactory, is_stub_mode
    
    return {
        "stub_mode_enabled": is_stub_mode(),
        "available_stubs": StubFactory.list_available_stubs(),
    }


@router.get("/bhuvan/scenes")
async def test_bhuvan_stub(limit: int = 5) -> List[Dict]:
    """Test Bhuvan stub - get mock satellite scenes."""
    from app.stubs.factory import get_stub
    
    stub = get_stub("bhuvan")
    return stub.get_mock_data(limit)


@router.get("/bhuvan/satellites")
async def get_bhuvan_satellites() -> List[Dict]:
    """Get available Bhuvan satellites."""
    from app.stubs.factory import get_stub
    
    stub = get_stub("bhuvan")
    return stub.get_available_satellites()


@router.get("/nrsc/products")
async def test_nrsc_stub() -> List[Dict]:
    """Test NRSC stub - get available products."""
    from app.stubs.factory import get_stub
    
    stub = get_stub("nrsc")
    return stub.get_available_products()


@router.get("/apsac/layers")
async def test_apsac_stub(category: str = None) -> Dict[str, Any]:
    """Test APSAC stub - get GIS layers."""
    from app.stubs.factory import get_stub
    
    stub = get_stub("apsac")
    return await stub.list_layers(category=category)


@router.get("/apsac/categories")
async def get_apsac_categories() -> List[Dict]:
    """Get APSAC layer categories."""
    from app.stubs.factory import get_stub
    
    stub = get_stub("apsac")
    return stub.get_categories()


@router.get("/cdma/properties")
async def test_cdma_stub(municipality: str = None, limit: int = 10) -> Dict[str, Any]:
    """Test CDMA stub - search property records."""
    from app.stubs.factory import get_stub
    
    stub = get_stub("cdma")
    return await stub.search_properties(municipality=municipality, limit=limit)


@router.get("/cdma/municipalities")
async def get_cdma_municipalities() -> List[str]:
    """Get CDMA municipalities."""
    from app.stubs.factory import get_stub
    
    stub = get_stub("cdma")
    return stub.get_municipalities()


@router.get("/sslr/records")
async def test_sslr_stub(district: str = None, limit: int = 10) -> Dict[str, Any]:
    """Test SSLR stub - search land records."""
    from app.stubs.factory import get_stub
    
    stub = get_stub("sslr")
    return await stub.search_records(district=district, limit=limit)


@router.get("/sslr/districts")
async def get_sslr_districts() -> List[str]:
    """Get SSLR districts."""
    from app.stubs.factory import get_stub
    
    stub = get_stub("sslr")
    return stub.get_districts()


@router.get("/meebhoomi/parcels")
async def test_meebhoomi_stub(district: str = None, limit: int = 10) -> Dict[str, Any]:
    """Test Meebhoomi stub - search cadastral parcels."""
    from app.stubs.factory import get_stub
    
    stub = get_stub("meebhoomi")
    return await stub.search_parcels(district=district, limit=limit)


@router.get("/gee/indices")
async def test_gee_stub() -> List[Dict]:
    """Test GEE stub - get available spectral indices."""
    from app.stubs.factory import get_stub
    
    stub = get_stub("gee")
    return stub.get_available_indices()


@router.get("/status")
async def get_all_stub_status() -> Dict[str, Any]:
    """Get status of all stubs."""
    from app.stubs.factory import StubFactory
    
    status = {}
    for stub_type in StubFactory.list_available_stubs():
        try:
            stub = StubFactory.get_stub(stub_type)
            status[stub_type] = {
                "available": stub.is_available(),
                "name": stub.name,
                "description": stub.description,
            }
        except Exception as e:
            status[stub_type] = {
                "available": False,
                "error": str(e),
            }
    
    return {
        "stubs": status,
        "total": len(status),
    }
