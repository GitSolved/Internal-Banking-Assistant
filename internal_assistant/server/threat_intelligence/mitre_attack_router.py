"""MITRE ATT&CK API endpoints for Internal Assistant."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Any, Optional

from internal_assistant.server.threat_intelligence.mitre_attack_service import (
    MitreAttackService,
    AttackDomain,
    AttackTechnique,
    AttackTactic,
    ThreatGroup,
)

mitre_attack_router = APIRouter(prefix="/v1/mitre-attack", tags=["MITRE ATT&CK"])


@mitre_attack_router.get("/techniques")
async def get_techniques(
    domain: str = Query("enterprise-attack", description="ATT&CK domain"),
    search: Optional[str] = Query(None, description="Search query"),
    banking_only: bool = Query(
        False, description="Show only banking-relevant techniques"
    ),
) -> List[Dict[str, Any]]:
    """Get MITRE ATT&CK techniques."""
    try:
        async with MitreAttackService() as mitre_service:
            # Validate domain
            try:
                attack_domain = AttackDomain(domain)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid domain: {domain}")

            # Fetch techniques
            techniques = await mitre_service.fetch_techniques(attack_domain)

            # Apply filters
            if search:
                techniques = mitre_service.search_techniques(search)

            if banking_only:
                techniques = mitre_service.get_banking_relevant_techniques()

            # Convert to dict format
            return [
                {
                    "technique_id": tech.technique_id,
                    "name": tech.name,
                    "description": tech.description,
                    "tactic": tech.tactic,
                    "platforms": tech.platforms,
                    "data_sources": tech.data_sources,
                    "detection": tech.detection,
                    "mitigation": tech.mitigation,
                    "url": tech.url,
                }
                for tech in techniques
            ]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching techniques: {str(e)}"
        )


@mitre_attack_router.get("/techniques/{technique_id}")
async def get_technique_by_id(technique_id: str) -> Dict[str, Any]:
    """Get specific MITRE ATT&CK technique by ID."""
    try:
        async with MitreAttackService() as mitre_service:
            await mitre_service.fetch_techniques()
            technique = mitre_service.get_technique_by_id(technique_id)

            if not technique:
                raise HTTPException(
                    status_code=404, detail=f"Technique {technique_id} not found"
                )

            return {
                "technique_id": technique.technique_id,
                "name": technique.name,
                "description": technique.description,
                "tactic": technique.tactic,
                "subtechniques": technique.subtechniques,
                "platforms": technique.platforms,
                "data_sources": technique.data_sources,
                "detection": technique.detection,
                "mitigation": technique.mitigation,
                "url": technique.url,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching technique: {str(e)}"
        )


@mitre_attack_router.get("/tactics")
async def get_tactics(
    domain: str = Query("enterprise-attack", description="ATT&CK domain")
) -> List[Dict[str, Any]]:
    """Get MITRE ATT&CK tactics."""
    try:
        async with MitreAttackService() as mitre_service:
            # Validate domain
            try:
                attack_domain = AttackDomain(domain)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid domain: {domain}")

            # Fetch tactics
            tactics = await mitre_service.fetch_tactics(attack_domain)

            # Convert to dict format
            return [
                {
                    "tactic_id": tactic.tactic_id,
                    "name": tactic.name,
                    "description": tactic.description,
                    "techniques": tactic.techniques,
                    "url": tactic.url,
                }
                for tactic in tactics
            ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tactics: {str(e)}")


@mitre_attack_router.get("/tactics/{tactic_id}")
async def get_tactic_by_id(tactic_id: str) -> Dict[str, Any]:
    """Get specific MITRE ATT&CK tactic by ID."""
    try:
        async with MitreAttackService() as mitre_service:
            await mitre_service.fetch_tactics()
            tactic = mitre_service.get_tactic_by_id(tactic_id)

            if not tactic:
                raise HTTPException(
                    status_code=404, detail=f"Tactic {tactic_id} not found"
                )

            return {
                "tactic_id": tactic.tactic_id,
                "name": tactic.name,
                "description": tactic.description,
                "techniques": tactic.techniques,
                "url": tactic.url,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tactic: {str(e)}")


@mitre_attack_router.get("/groups")
async def get_threat_groups(
    domain: str = Query("enterprise-attack", description="ATT&CK domain"),
    banking_only: bool = Query(False, description="Show only banking-targeting groups"),
) -> List[Dict[str, Any]]:
    """Get MITRE ATT&CK threat groups."""
    try:
        async with MitreAttackService() as mitre_service:
            # Validate domain
            try:
                attack_domain = AttackDomain(domain)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid domain: {domain}")

            # Fetch groups
            groups = await mitre_service.fetch_threat_groups(attack_domain)

            # Apply filters
            if banking_only:
                groups = mitre_service.get_banking_threat_groups()

            # Convert to dict format
            return [
                {
                    "group_id": group.group_id,
                    "name": group.name,
                    "description": group.description,
                    "aliases": group.aliases,
                    "techniques": group.techniques,
                    "targets": group.targets,
                    "url": group.url,
                }
                for group in groups
            ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching groups: {str(e)}")


@mitre_attack_router.get("/groups/{group_id}")
async def get_group_by_id(group_id: str) -> Dict[str, Any]:
    """Get specific MITRE ATT&CK threat group by ID."""
    try:
        async with MitreAttackService() as mitre_service:
            await mitre_service.fetch_threat_groups()
            group = mitre_service.get_group_by_id(group_id)

            if not group:
                raise HTTPException(
                    status_code=404, detail=f"Group {group_id} not found"
                )

            return {
                "group_id": group.group_id,
                "name": group.name,
                "description": group.description,
                "aliases": group.aliases,
                "techniques": group.techniques,
                "targets": group.targets,
                "url": group.url,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching group: {str(e)}")


@mitre_attack_router.get("/banking/techniques")
async def get_banking_techniques() -> List[Dict[str, Any]]:
    """Get banking-relevant MITRE ATT&CK techniques."""
    try:
        async with MitreAttackService() as mitre_service:
            await mitre_service.fetch_techniques()
            techniques = mitre_service.get_banking_relevant_techniques()

            return [
                {
                    "technique_id": tech.technique_id,
                    "name": tech.name,
                    "description": tech.description,
                    "tactic": tech.tactic,
                    "platforms": tech.platforms,
                    "data_sources": tech.data_sources,
                    "detection": tech.detection,
                    "mitigation": tech.mitigation,
                    "url": tech.url,
                }
                for tech in techniques
            ]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching banking techniques: {str(e)}"
        )


@mitre_attack_router.get("/banking/groups")
async def get_banking_groups() -> List[Dict[str, Any]]:
    """Get banking-targeting MITRE ATT&CK threat groups."""
    try:
        async with MitreAttackService() as mitre_service:
            await mitre_service.fetch_threat_groups()
            groups = mitre_service.get_banking_threat_groups()

            return [
                {
                    "group_id": group.group_id,
                    "name": group.name,
                    "description": group.description,
                    "aliases": group.aliases,
                    "techniques": group.techniques,
                    "targets": group.targets,
                    "url": group.url,
                }
                for group in groups
            ]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching banking groups: {str(e)}"
        )


@mitre_attack_router.get("/search")
async def search_mitre_data(
    query: str = Query(..., description="Search query"),
    domain: str = Query("enterprise-attack", description="ATT&CK domain"),
) -> Dict[str, Any]:
    """Search MITRE ATT&CK data."""
    try:
        async with MitreAttackService() as mitre_service:
            # Validate domain
            try:
                attack_domain = AttackDomain(domain)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid domain: {domain}")

            # Fetch data
            await mitre_service.fetch_techniques(attack_domain)
            await mitre_service.fetch_tactics(attack_domain)
            await mitre_service.fetch_threat_groups(attack_domain)

            # Search techniques
            techniques = mitre_service.search_techniques(query)

            # Search tactics (simple text search)
            tactics = []
            for tactic in mitre_service._tactics_cache.values():
                if (
                    query.lower() in tactic.name.lower()
                    or query.lower() in tactic.description.lower()
                ):
                    tactics.append(tactic)

            # Search groups (simple text search)
            groups = []
            for group in mitre_service._groups_cache.values():
                if (
                    query.lower() in group.name.lower()
                    or query.lower() in group.description.lower()
                    or any(query.lower() in alias.lower() for alias in group.aliases)
                ):
                    groups.append(group)

            return {
                "query": query,
                "results": {
                    "techniques": [
                        {
                            "technique_id": tech.technique_id,
                            "name": tech.name,
                            "description": (
                                tech.description[:200] + "..."
                                if len(tech.description) > 200
                                else tech.description
                            ),
                            "tactic": tech.tactic,
                            "url": tech.url,
                        }
                        for tech in techniques
                    ],
                    "tactics": [
                        {
                            "tactic_id": tactic.tactic_id,
                            "name": tactic.name,
                            "description": (
                                tactic.description[:200] + "..."
                                if len(tactic.description) > 200
                                else tactic.description
                            ),
                            "url": tactic.url,
                        }
                        for tactic in tactics
                    ],
                    "groups": [
                        {
                            "group_id": group.group_id,
                            "name": group.name,
                            "description": (
                                group.description[:200] + "..."
                                if len(group.description) > 200
                                else group.description
                            ),
                            "aliases": group.aliases,
                            "url": group.url,
                        }
                        for group in groups
                    ],
                },
                "summary": {
                    "total_techniques": len(techniques),
                    "total_tactics": len(tactics),
                    "total_groups": len(groups),
                },
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching MITRE data: {str(e)}"
        )


@mitre_attack_router.get("/cache/info")
async def get_cache_info() -> Dict[str, Any]:
    """Get MITRE ATT&CK cache information."""
    try:
        async with MitreAttackService() as mitre_service:
            return mitre_service.get_cache_info()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting cache info: {str(e)}"
        )


@mitre_attack_router.post("/refresh")
async def refresh_mitre_data() -> Dict[str, Any]:
    """Refresh MITRE ATT&CK data cache."""
    try:
        async with MitreAttackService() as mitre_service:
            success = await mitre_service.refresh_data()
            if success:
                return {
                    "status": "success",
                    "message": "MITRE ATT&CK data refreshed successfully",
                }
            else:
                raise HTTPException(
                    status_code=500, detail="Failed to refresh MITRE ATT&CK data"
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing data: {str(e)}")
