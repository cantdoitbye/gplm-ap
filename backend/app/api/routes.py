"""
API Routes

Main router that includes all sub-routers.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def api_root():
    """API v1 root endpoint."""
    return {
        "message": "AIKOSH-5 API v1",
        "endpoints": {
            "pda": "/api/v1/pda",
            "cda": "/api/v1/cda",
            "gua": "/api/v1/gua",
            "dashboard": "/api/v1/dashboard",
            "auth": "/api/v1/auth",
            "workflows": "/api/v1/workflows",
            "notifications": "/api/v1/notifications",
            "export": "/api/v1/export",
        }
    }


from app.api import pda, cda, gua, dashboard, auth, workflows, notifications, export

router.include_router(pda.router, prefix="/pda", tags=["Property Detection Agent (PDA)"])
router.include_router(cda.router, prefix="/cda", tags=["Change Detection Agent (CDA)"])
router.include_router(gua.router, prefix="/gua", tags=["GIS Auto-Update Agent (GUA)"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["Urban Planning Dashboard"])
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
router.include_router(export.router, prefix="/export", tags=["Export"])
