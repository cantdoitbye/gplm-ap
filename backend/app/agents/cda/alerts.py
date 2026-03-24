"""
Alert Generation Module for Change Detection Agent

Generates and manages alerts from detected changes.
"""

import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from app.agents.cda.comparator import ChangeArea, Severity

logger = logging.getLogger(__name__)


class AlertStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


@dataclass
class Alert:
    """Alert generated from change detection."""
    alert_id: str
    title: str
    description: str
    severity: Severity
    status: AlertStatus
    change_id: str
    change_type: str
    municipality_id: Optional[int] = None
    property_id: Optional[int] = None
    geometry: Optional[Dict[str, Any]] = None
    area_sqm: float = 0.0
    confidence: float = 0.0
    assigned_to: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "status": self.status.value,
            "change_id": self.change_id,
            "change_type": self.change_type,
            "municipality_id": self.municipality_id,
            "property_id": self.property_id,
            "area_sqm": round(self.area_sqm, 2),
            "confidence": round(self.confidence, 4),
            "assigned_to": self.assigned_to,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat(),
        }


class AlertGenerator:
    """
    Generates alerts from detected changes.
    
    Applies rules to determine:
    - Alert priority and severity
    - Alert deduplication
    - Notification routing
    """
    
    ALERT_TEMPLATES = {
        "new_construction": {
            "title": "New Construction Detected",
            "description": "A new building/structure has been detected in {area_name}. "
                          "Area: {area_sqm:.0f} sqm. This may require verification.",
        },
        "expansion": {
            "title": "Building Expansion Detected",
            "description": "An existing building appears to have been expanded. "
                          "Additional area: {area_sqm:.0f} sqm.",
        },
        "demolition": {
            "title": "Demolition Detected",
            "description": "A structure appears to have been demolished. "
                          "Previous area: {area_sqm:.0f} sqm. Please verify.",
        },
        "encroachment": {
            "title": "Potential Encroachment Detected",
            "description": "Potential unauthorized construction detected. "
                          "Area: {area_sqm:.0f} sqm. Immediate verification recommended.",
        },
        "vegetation_change": {
            "title": "Vegetation Change Detected",
            "description": "Significant vegetation change detected. "
                          "Affected area: {area_sqm:.0f} sqm.",
        },
        "water_change": {
            "title": "Water Body Change Detected",
            "description": "Change in water body extent detected. "
                          "Affected area: {area_sqm:.0f} sqm.",
        },
    }
    
    SEVERITY_ESCALATION = {
        Severity.CRITICAL: {"timeout_hours": 4, "escalate_to": "department_head"},
        Severity.HIGH: {"timeout_hours": 24, "escalate_to": "senior_officer"},
        Severity.MEDIUM: {"timeout_hours": 72, "escalate_to": "officer"},
        Severity.LOW: {"timeout_hours": 168, "escalate_to": None},
    }
    
    def __init__(
        self,
        min_confidence: float = 0.5,
        deduplication_window_hours: int = 24,
    ):
        self.min_confidence = min_confidence
        self.deduplication_window = deduplication_window_hours
        self.recent_alerts: List[Alert] = []
    
    def generate_alerts(
        self,
        changes: List[ChangeArea],
        municipality_id: int = None,
        area_name: str = "the monitoring area",
    ) -> List[Alert]:
        """
        Generate alerts from detected changes.
        
        Args:
            changes: List of detected changes
            municipality_id: Municipality ID
            area_name: Name of the area for descriptions
        
        Returns:
            List of generated alerts
        """
        alerts = []
        
        for change in changes:
            if change.confidence < self.min_confidence:
                continue
            
            if self._is_duplicate(change):
                logger.debug(f"Skipping duplicate alert for change {change.change_id}")
                continue
            
            template = self.ALERT_TEMPLATES.get(
                change.change_type.value,
                self.ALERT_TEMPLATES.get("new_construction")
            )
            
            title = template["title"]
            description = template["description"].format(
                area_name=area_name,
                area_sqm=change.area_sqm,
            )
            
            alert = Alert(
                alert_id=str(uuid.uuid4()),
                title=title,
                description=description,
                severity=change.severity,
                status=AlertStatus.NEW,
                change_id=change.change_id,
                change_type=change.change_type.value,
                municipality_id=municipality_id,
                geometry=change.geometry,
                area_sqm=change.area_sqm,
                confidence=change.confidence,
            )
            
            alerts.append(alert)
            self.recent_alerts.append(alert)
        
        self._cleanup_old_alerts()
        
        logger.info(f"Generated {len(alerts)} alerts from {len(changes)} changes")
        
        return alerts
    
    def _is_duplicate(self, change: ChangeArea) -> bool:
        """Check if an alert for this change already exists."""
        cutoff = datetime.utcnow()
        
        for alert in self.recent_alerts:
            if alert.change_id == change.change_id:
                return True
            
            if (alert.change_type == change.change_type.value and
                alert.area_sqm == change.area_sqm and
                (cutoff - alert.created_at).total_seconds() < self.deduplication_window * 3600):
                return True
        
        return False
    
    def _cleanup_old_alerts(self):
        """Remove old alerts from recent_alerts cache."""
        cutoff = datetime.utcnow()
        self.recent_alerts = [
            a for a in self.recent_alerts
            if (cutoff - a.created_at).total_seconds() < self.deduplication_window * 3600 * 2
        ]
    
    def acknowledge_alert(
        self,
        alert: Alert,
        acknowledged_by: str,
    ) -> Alert:
        """Acknowledge an alert."""
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.assigned_to = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()
        return alert
    
    def resolve_alert(
        self,
        alert: Alert,
        resolved_by: str,
        is_authorised: bool,
        notes: str = None,
    ) -> Alert:
        """Resolve an alert."""
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.resolution_notes = notes or ("Authorised" if is_authorised else "Unauthorised - action required")
        return alert
    
    def get_alert_statistics(self, alerts: List[Alert]) -> Dict[str, Any]:
        """Get statistics about alerts."""
        by_severity = {s.value: 0 for s in Severity}
        by_status = {s.value: 0 for s in AlertStatus}
        by_type = {}
        
        for alert in alerts:
            by_severity[alert.severity.value] += 1
            by_status[alert.status.value] += 1
            
            ctype = alert.change_type
            if ctype not in by_type:
                by_type[ctype] = 0
            by_type[ctype] += 1
        
        return {
            "total_alerts": len(alerts),
            "by_severity": by_severity,
            "by_status": by_status,
            "by_type": by_type,
        }
