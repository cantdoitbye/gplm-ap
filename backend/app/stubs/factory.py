"""
Stub Factory

Factory for creating stub instances based on configuration.
"""

from typing import Any, Dict, Optional, Type
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class StubFactory:
    """
    Factory for creating stub instances.
    
    Usage:
        factory = StubFactory()
        bhuvan_stub = factory.get_stub("bhuvan")
        cdma_stub = factory.get_stub("cdma")
    """
    
    _stubs: Dict[str, Any] = {}
    
    @classmethod
    def get_stub(cls, stub_type: str):
        """
        Get a stub instance by type.
        
        Args:
            stub_type: Type of stub (bhuvan, nrsc, apsac, cdma, sslr, meebhoomi)
        
        Returns:
            Stub instance
        """
        if not getattr(settings, "USE_API_STUBS", True):
            raise RuntimeError(f"Stubs are disabled. Set USE_API_STUBS=True to use stubs.")
        
        if stub_type not in cls._stubs:
            cls._stubs[stub_type] = cls._create_stub(stub_type)
        
        return cls._stubs[stub_type]
    
    @classmethod
    def _create_stub(cls, stub_type: str):
        """Create a new stub instance."""
        from app.stubs.bhuvan_stub import BhuvanStub
        from app.stubs.nrsc_stub import NRSCStub
        from app.stubs.apsac_stub import APSACStub
        from app.stubs.cdma_stub import CDMAStub
        from app.stubs.sslr_stub import SSLRStub
        from app.stubs.meebhoomi_stub import MeebhoomiStub
        from app.stubs.copernicus_stub import CopernicusStub
        from app.stubs.gee_stub import GEEStub
        
        stub_classes = {
            "bhuvan": BhuvanStub,
            "isro": BhuvanStub,
            "nrsc": NRSCStub,
            "apsac": APSACStub,
            "cdma": CDMAStub,
            "sslr": SSLRStub,
            "meebhoomi": MeebhoomiStub,
            "copernicus": CopernicusStub,
            "sentinel": CopernicusStub,
            "gee": GEEStub,
        }
        
        if stub_type not in stub_classes:
            raise ValueError(f"Unknown stub type: {stub_type}. Available: {list(stub_classes.keys())}")
        
        logger.info(f"[STUB] Creating stub instance: {stub_type}")
        return stub_classes[stub_type]()
    
    @classmethod
    def clear_stubs(cls):
        """Clear all cached stub instances."""
        cls._stubs.clear()
    
    @classmethod
    def list_available_stubs(cls) -> list:
        """List all available stub types."""
        return ["bhuvan", "isro", "nrsc", "apsac", "cdma", "sslr", "meebhoomi", "copernicus", "sentinel", "gee"]
    
    @classmethod
    def get_all_stubs(cls) -> Dict[str, Any]:
        """Get all stub instances."""
        return {stub_type: cls.get_stub(stub_type) for stub_type in cls.list_available_stubs()}


def get_stub(stub_type: str):
    """Convenience function to get a stub."""
    return StubFactory.get_stub(stub_type)


def is_stub_mode() -> bool:
    """Check if stub mode is enabled."""
    return getattr(settings, "USE_API_STUBS", True)


def get_satellite_stub():
    """Get the primary satellite imagery stub (Bhuvan for Indian context)."""
    return get_stub("bhuvan")


def get_gis_stub():
    """Get the primary GIS layers stub (APSAC for AP context)."""
    return get_stub("apsac")


def get_property_stub():
    """Get the property records stub (CDMA for municipal records)."""
    return get_stub("cdma")


def get_land_stub():
    """Get the land records stub (SSLR for land ownership)."""
    return get_stub("sslr")


def get_cadastral_stub():
    """Get the cadastral data stub (Meebhoomi for boundaries)."""
    return get_stub("meebhoomi")
