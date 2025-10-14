"""Threat Intelligence API endpoints for Internal Assistant."""

from fastapi import APIRouter, Depends, Request
from typing import Dict, List, Any

from internal_assistant.server.feeds.feeds_service import RSSFeedService
from internal_assistant.server.threat_intelligence.threat_analyzer import (
    ThreatIndicator,
    SecurityRecommendation,
)

threat_intelligence_router = APIRouter(
    prefix="/v1/threat-intelligence", tags=["Threat Intelligence"]
)


@threat_intelligence_router.get("/threats")
def get_current_threats(
    feed_service: RSSFeedService = Depends(),
) -> List[Dict[str, Any]]:
    """Get current cyber threats from analyzed feeds."""
    threats = feed_service.analyze_threats()

    return [
        {
            "indicator": threat.indicator,
            "threat_type": threat.threat_type.value,
            "threat_level": threat.threat_level.value,
            "description": threat.description,
            "source": threat.source,
            "timestamp": threat.timestamp.isoformat(),
            "ioc_type": threat.ioc_type,
            "confidence": threat.confidence,
        }
        for threat in threats
    ]


@threat_intelligence_router.get("/recommendations")
def get_security_recommendations(
    feed_service: RSSFeedService = Depends(),
) -> List[Dict[str, Any]]:
    """Get security recommendations based on threat analysis."""
    recommendations = feed_service.get_security_recommendations()

    return [
        {
            "title": rec.title,
            "description": rec.description,
            "priority": rec.priority.value,
            "action_items": rec.action_items,
            "affected_systems": rec.affected_systems,
            "estimated_effort": rec.estimated_effort,
            "compliance_impact": rec.compliance_impact,
        }
        for rec in recommendations
    ]


@threat_intelligence_router.get("/summary")
def get_threat_summary(feed_service: RSSFeedService = Depends()) -> Dict[str, Any]:
    """Get a summary of current threat landscape."""
    return feed_service.get_threat_summary()


@threat_intelligence_router.get("/threats/critical")
def get_critical_threats(
    feed_service: RSSFeedService = Depends(),
) -> List[Dict[str, Any]]:
    """Get only critical threats requiring immediate attention."""
    threats = feed_service.analyze_threats()
    critical_threats = [t for t in threats if t.threat_level.value == "critical"]

    return [
        {
            "indicator": threat.indicator,
            "threat_type": threat.threat_type.value,
            "description": threat.description,
            "source": threat.source,
            "timestamp": threat.timestamp.isoformat(),
            "ioc_type": threat.ioc_type,
            "confidence": threat.confidence,
        }
        for threat in critical_threats
    ]


@threat_intelligence_router.get("/threats/banking-specific")
def get_banking_specific_threats(
    feed_service: RSSFeedService = Depends(),
) -> List[Dict[str, Any]]:
    """Get threats specifically targeting banking/financial institutions."""
    threats = feed_service.analyze_threats()
    banking_threats = [
        t
        for t in threats
        if any(
            kw in t.description.lower()
            for kw in ["bank", "financial", "payment", "transaction"]
        )
    ]

    return [
        {
            "indicator": threat.indicator,
            "threat_type": threat.threat_type.value,
            "threat_level": threat.threat_level.value,
            "description": threat.description,
            "source": threat.source,
            "timestamp": threat.timestamp.isoformat(),
            "ioc_type": threat.ioc_type,
            "confidence": threat.confidence,
        }
        for threat in banking_threats
    ]


@threat_intelligence_router.get("/recommendations/priority/{priority}")
def get_recommendations_by_priority(
    priority: str, feed_service: RSSFeedService = Depends()
) -> List[Dict[str, Any]]:
    """Get security recommendations filtered by priority level."""
    recommendations = feed_service.get_security_recommendations()
    filtered_recs = [r for r in recommendations if r.priority.value == priority.lower()]

    return [
        {
            "title": rec.title,
            "description": rec.description,
            "priority": rec.priority.value,
            "action_items": rec.action_items,
            "affected_systems": rec.affected_systems,
            "estimated_effort": rec.estimated_effort,
            "compliance_impact": rec.compliance_impact,
        }
        for rec in filtered_recs
    ]


@threat_intelligence_router.get("/indicators/{ioc_type}")
def get_indicators_by_type(
    ioc_type: str, feed_service: RSSFeedService = Depends()
) -> List[Dict[str, Any]]:
    """Get threat indicators filtered by IOC type (IP, domain, hash)."""
    threats = feed_service.analyze_threats()
    filtered_threats = [t for t in threats if t.ioc_type.lower() == ioc_type.lower()]

    return [
        {
            "indicator": threat.indicator,
            "threat_type": threat.threat_type.value,
            "threat_level": threat.threat_level.value,
            "description": threat.description,
            "source": threat.source,
            "timestamp": threat.timestamp.isoformat(),
            "confidence": threat.confidence,
        }
        for threat in filtered_threats
    ]


@threat_intelligence_router.get("/compliance-impact")
def get_compliance_impact_analysis(
    feed_service: RSSFeedService = Depends(),
) -> Dict[str, Any]:
    """Get analysis of how current threats impact banking compliance."""
    recommendations = feed_service.get_security_recommendations()

    compliance_impacts = {}
    for rec in recommendations:
        for compliance in rec.compliance_impact:
            if compliance not in compliance_impacts:
                compliance_impacts[compliance] = {
                    "recommendations": [],
                    "priority_count": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                }

            compliance_impacts[compliance]["recommendations"].append(
                {
                    "title": rec.title,
                    "priority": rec.priority.value,
                    "action_items": rec.action_items,
                }
            )

            compliance_impacts[compliance]["priority_count"][rec.priority.value] += 1

    return {
        "compliance_impacts": compliance_impacts,
        "total_recommendations": len(recommendations),
        "affected_compliance_frameworks": list(compliance_impacts.keys()),
    }
