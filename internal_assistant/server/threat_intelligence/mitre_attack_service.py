"""MITRE ATT&CK Integration Service for Internal Assistant."""

import asyncio
import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)


class AttackDomain(Enum):
    """MITRE ATT&CK domains."""
    ENTERPRISE = "enterprise-attack"
    MOBILE = "mobile-attack"
    ICS = "ics-attack"


@dataclass
class AttackTechnique:
    """Represents a MITRE ATT&CK technique."""
    technique_id: str
    name: str
    description: str
    tactic: str
    subtechniques: List[str]
    platforms: List[str]
    data_sources: List[str]
    detection: Optional[str]
    mitigation: Optional[str]
    url: str


@dataclass
class AttackTactic:
    """Represents a MITRE ATT&CK tactic."""
    tactic_id: str
    name: str
    description: str
    techniques: List[str]
    url: str


@dataclass
class ThreatGroup:
    """Represents a MITRE ATT&CK threat group."""
    group_id: str
    name: str
    description: str
    aliases: List[str]
    techniques: List[str]
    targets: List[str]
    url: str


class MitreAttackService:
    """Service for integrating with MITRE ATT&CK framework."""
    
    BASE_URL = "https://attack.mitre.org/api/"
    
    # Storage paths
    STORAGE_DIR = Path("local_data/internal_assistant/mitre_attack")
    TECHNIQUES_FILE = STORAGE_DIR / "techniques.json"
    TACTICS_FILE = STORAGE_DIR / "tactics.json"
    GROUPS_FILE = STORAGE_DIR / "groups.json"
    CACHE_INFO_FILE = STORAGE_DIR / "cache_info.json"
    
    # Banking-specific threat groups and techniques
    BANKING_THREAT_GROUPS = [
        "APT29", "APT28", "Lazarus Group", "Carbanak", "Cobalt Group",
        "FIN7", "FIN8", "FIN9", "LAPSUS$", "Conti", "REvil"
    ]
    
    BANKING_TECHNIQUES = [
        "T1078.004",  # Valid Accounts: Cloud Accounts
        "T1078.002",  # Valid Accounts: Domain Accounts
        "T1566.001",  # Phishing: Spearphishing Attachment
        "T1566.002",  # Phishing: Spearphishing Link
        "T1071.001",  # Application Layer Protocol: Web Protocols
        "T1071.004",  # Application Layer Protocol: DNS
        "T1105",      # Ingress Tool Transfer
        "T1059.001",  # Command and Scripting Interpreter: PowerShell
        "T1059.003",  # Command and Scripting Interpreter: Windows Command Shell
        "T1083",      # File and Directory Discovery
        "T1082",      # System Information Discovery
        "T1018",      # Remote System Discovery
        "T1057",      # Process Discovery
        "T1049",      # System Network Connections Discovery
        "T1016",      # System Network Configuration Discovery
        "T1007",      # System Service Discovery
        "T1482",      # Domain Trust Discovery
        "T1087.002",  # Account Discovery: Domain Account
        "T1087.001",  # Account Discovery: Local Account
        "T1010",      # Application Window Discovery
        "T1213",      # Data from Information Repositories
        "T1005",      # Data from Local System
        "T1039",      # Data from Network Shared Drive
        "T1025",      # Data from Removable Media
        "T1074.001",  # Data Staged: Local Data Staging
        "T1074.002",  # Data Staged: Remote Data Staging
        "T1560.001",  # Archive Collected Data: Archive via Utility
        "T1560.002",  # Archive Collected Data: Archive via Library
        "T1560.003",  # Archive Collected Data: Archive via Custom Method
        "T1041",      # Exfiltration Over C2 Channel
        "T1048.003",  # Exfiltration Over Alternative Protocol: Exfiltration Over Unencrypted/Obfuscated Non-C2 Protocol
        "T1011.001",  # Exfiltration Over Other Network Medium: Exfiltration Over USB
        "T1052.001",  # Exfiltration Over Physical Medium: Exfiltration over USB
        "T1052.002",  # Exfiltration Over Physical Medium: Exfiltration over Network Medium
        "T1011",      # Exfiltration Over Other Network Medium
        "T1052",      # Exfiltration Over Physical Medium
        "T1071.002",  # Application Layer Protocol: File Transfer Protocols
        "T1071.003",  # Application Layer Protocol: Mail Protocols
        "T1071.004",  # Application Layer Protocol: DNS
        "T1071.001",  # Application Layer Protocol: Web Protocols
        "T1090",      # Proxy
        "T1090.001",  # Proxy: Internal Proxy
        "T1090.002",  # Proxy: External Proxy
        "T1090.003",  # Proxy: Multi-hop Proxy
        "T1090.004",  # Proxy: Domain Fronting
        "T1219",      # Remote Access Software
        "T1133",      # External Remote Services
        "T1021.001",  # Remote Services: Remote Desktop Protocol
        "T1021.002",  # Remote Services: SMB/Windows Admin Shares
        "T1021.003",  # Remote Services: Distributed Component Object Model
        "T1021.004",  # Remote Services: SSH
        "T1021.005",  # Remote Services: VNC
        "T1021.006",  # Remote Services: Windows Remote Management
        "T1078.001",  # Valid Accounts: Default Accounts
        "T1078.002",  # Valid Accounts: Domain Accounts
        "T1078.003",  # Valid Accounts: Local Accounts
        "T1078.004",  # Valid Accounts: Cloud Accounts
        "T1136.001",  # Create Account: Local Account
        "T1136.002",  # Create Account: Domain Account
        "T1136.003",  # Create Account: Cloud Account
        "T1078.001",  # Valid Accounts: Default Accounts
        "T1078.002",  # Valid Accounts: Domain Accounts
        "T1078.003",  # Valid Accounts: Local Accounts
        "T1078.004",  # Valid Accounts: Cloud Accounts
        "T1136.001",  # Create Account: Local Account
        "T1136.002",  # Create Account: Domain Account
        "T1136.003",  # Create Account: Cloud Account
        "T1078.001",  # Valid Accounts: Default Accounts
        "T1078.002",  # Valid Accounts: Domain Accounts
        "T1078.003",  # Valid Accounts: Local Accounts
        "T1078.004",  # Valid Accounts: Cloud Accounts
        "T1136.001",  # Create Account: Local Account
        "T1136.002",  # Create Account: Domain Account
        "T1136.003",  # Create Account: Cloud Account
    ]
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._techniques_cache: Dict[str, AttackTechnique] = {}
        self._tactics_cache: Dict[str, AttackTactic] = {}
        self._groups_cache: Dict[str, ThreatGroup] = {}
        self._last_refresh: Optional[datetime] = None
        
        # Ensure storage directory exists
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load cached data from disk if available
        self._load_cached_data()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
    
    async def fetch_techniques(self, domain: AttackDomain = AttackDomain.ENTERPRISE) -> List[AttackTechnique]:
        """Fetch MITRE ATT&CK techniques."""
        if not self._session:
            raise RuntimeError("Service must be used within async context manager")
        
        try:
            url = f"{self.BASE_URL}techniques/{domain.value}/"
            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch techniques: HTTP {response.status}")
                    return []
                
                data = await response.json()
                techniques = []
                
                for item in data:
                    try:
                        technique = AttackTechnique(
                            technique_id=item.get("attack_id", ""),
                            name=item.get("name", ""),
                            description=item.get("description", ""),
                            tactic=item.get("tactic", ""),
                            subtechniques=item.get("subtechniques", []),
                            platforms=item.get("platforms", []),
                            data_sources=item.get("data_sources", []),
                            detection=item.get("detection", ""),
                            mitigation=item.get("mitigation", ""),
                            url=item.get("url", "")
                        )
                        techniques.append(technique)
                        self._techniques_cache[technique.technique_id] = technique
                        
                    except Exception as e:
                        logger.warning(f"Error parsing technique: {e}")
                        continue
                
                logger.info(f"Fetched {len(techniques)} techniques from MITRE ATT&CK")
                return techniques
                
        except Exception as e:
            logger.error(f"Error fetching techniques: {e}")
            return []
    
    async def fetch_tactics(self, domain: AttackDomain = AttackDomain.ENTERPRISE) -> List[AttackTactic]:
        """Fetch MITRE ATT&CK tactics."""
        if not self._session:
            raise RuntimeError("Service must be used within async context manager")
        
        try:
            url = f"{self.BASE_URL}tactics/{domain.value}/"
            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch tactics: HTTP {response.status}")
                    return []
                
                data = await response.json()
                tactics = []
                
                for item in data:
                    try:
                        tactic = AttackTactic(
                            tactic_id=item.get("attack_id", ""),
                            name=item.get("name", ""),
                            description=item.get("description", ""),
                            techniques=item.get("techniques", []),
                            url=item.get("url", "")
                        )
                        tactics.append(tactic)
                        self._tactics_cache[tactic.tactic_id] = tactic
                        
                    except Exception as e:
                        logger.warning(f"Error parsing tactic: {e}")
                        continue
                
                logger.info(f"Fetched {len(tactics)} tactics from MITRE ATT&CK")
                return tactics
                
        except Exception as e:
            logger.error(f"Error fetching tactics: {e}")
            return []
    
    async def fetch_threat_groups(self, domain: AttackDomain = AttackDomain.ENTERPRISE) -> List[ThreatGroup]:
        """Fetch MITRE ATT&CK threat groups."""
        if not self._session:
            raise RuntimeError("Service must be used within async context manager")
        
        try:
            url = f"{self.BASE_URL}groups/{domain.value}/"
            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch groups: HTTP {response.status}")
                    return []
                
                data = await response.json()
                groups = []
                
                for item in data:
                    try:
                        group = ThreatGroup(
                            group_id=item.get("attack_id", ""),
                            name=item.get("name", ""),
                            description=item.get("description", ""),
                            aliases=item.get("aliases", []),
                            techniques=item.get("techniques", []),
                            targets=item.get("targets", []),
                            url=item.get("url", "")
                        )
                        groups.append(group)
                        self._groups_cache[group.group_id] = group
                        
                    except Exception as e:
                        logger.warning(f"Error parsing group: {e}")
                        continue
                
                logger.info(f"Fetched {len(groups)} threat groups from MITRE ATT&CK")
                return groups
                
        except Exception as e:
            logger.error(f"Error fetching groups: {e}")
            return []
    
    def get_banking_relevant_techniques(self) -> List[AttackTechnique]:
        """Get techniques relevant to banking/financial sector."""
        banking_techniques = []
        
        for technique_id in self.BANKING_TECHNIQUES:
            if technique_id in self._techniques_cache:
                banking_techniques.append(self._techniques_cache[technique_id])
        
        return banking_techniques
    
    def get_banking_threat_groups(self) -> List[ThreatGroup]:
        """Get threat groups targeting banking/financial sector."""
        banking_groups = []
        
        for group in self._groups_cache.values():
            if any(alias in self.BANKING_THREAT_GROUPS for alias in group.aliases):
                banking_groups.append(group)
        
        return banking_groups
    
    def search_techniques(self, query: str) -> List[AttackTechnique]:
        """Search techniques by name or description."""
        results = []
        query_lower = query.lower()
        
        for technique in self._techniques_cache.values():
            if (query_lower in technique.name.lower() or 
                query_lower in technique.description.lower()):
                results.append(technique)
        
        return results
    
    def get_technique_by_id(self, technique_id: str) -> Optional[AttackTechnique]:
        """Get technique by ID."""
        return self._techniques_cache.get(technique_id)
    
    def get_tactic_by_id(self, tactic_id: str) -> Optional[AttackTactic]:
        """Get tactic by ID."""
        return self._tactics_cache.get(tactic_id)
    
    def get_group_by_id(self, group_id: str) -> Optional[ThreatGroup]:
        """Get threat group by ID."""
        return self._groups_cache.get(group_id)
    
    async def refresh_data(self) -> bool:
        """Refresh all MITRE ATT&CK data."""
        try:
            await self.fetch_techniques()
            await self.fetch_tactics()
            await self.fetch_threat_groups()
            self._last_refresh = datetime.now(timezone.utc)
            
            # Save to disk after successful refresh
            self._save_cached_data()
            
            return True
        except Exception as e:
            logger.error(f"Error refreshing MITRE ATT&CK data: {e}")
            return False
    
    def _load_cached_data(self):
        """Load cached data from disk."""
        try:
            # Load techniques
            if self.TECHNIQUES_FILE.exists():
                with open(self.TECHNIQUES_FILE, 'r') as f:
                    data = json.load(f)
                    for tech_data in data.values():
                        technique = AttackTechnique(**tech_data)
                        self._techniques_cache[technique.technique_id] = technique
                logger.info(f"Loaded {len(self._techniques_cache)} techniques from cache")
            
            # Load tactics
            if self.TACTICS_FILE.exists():
                with open(self.TACTICS_FILE, 'r') as f:
                    data = json.load(f)
                    for tactic_data in data.values():
                        tactic = AttackTactic(**tactic_data)
                        self._tactics_cache[tactic.tactic_id] = tactic
                logger.info(f"Loaded {len(self._tactics_cache)} tactics from cache")
            
            # Load groups
            if self.GROUPS_FILE.exists():
                with open(self.GROUPS_FILE, 'r') as f:
                    data = json.load(f)
                    for group_data in data.values():
                        group = ThreatGroup(**group_data)
                        self._groups_cache[group.group_id] = group
                logger.info(f"Loaded {len(self._groups_cache)} groups from cache")
            
            # Load cache info
            if self.CACHE_INFO_FILE.exists():
                with open(self.CACHE_INFO_FILE, 'r') as f:
                    cache_info = json.load(f)
                    if cache_info.get("last_refresh"):
                        self._last_refresh = datetime.fromisoformat(cache_info["last_refresh"])
                        
        except Exception as e:
            logger.warning(f"Error loading cached data: {e}")
    
    def _save_cached_data(self):
        """Save cached data to disk."""
        try:
            # Save techniques
            techniques_data = {
                tech_id: asdict(technique) 
                for tech_id, technique in self._techniques_cache.items()
            }
            with open(self.TECHNIQUES_FILE, 'w') as f:
                json.dump(techniques_data, f, indent=2)
            
            # Save tactics
            tactics_data = {
                tactic_id: asdict(tactic) 
                for tactic_id, tactic in self._tactics_cache.items()
            }
            with open(self.TACTICS_FILE, 'w') as f:
                json.dump(tactics_data, f, indent=2)
            
            # Save groups
            groups_data = {
                group_id: asdict(group) 
                for group_id, group in self._groups_cache.items()
            }
            with open(self.GROUPS_FILE, 'w') as f:
                json.dump(groups_data, f, indent=2)
            
            # Save cache info
            cache_info = self.get_cache_info()
            with open(self.CACHE_INFO_FILE, 'w') as f:
                json.dump(cache_info, f, indent=2)
                
            logger.info("MITRE ATT&CK data saved to disk")
            
        except Exception as e:
            logger.error(f"Error saving cached data: {e}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information."""
        return {
            "techniques_count": len(self._techniques_cache),
            "tactics_count": len(self._tactics_cache),
            "groups_count": len(self._groups_cache),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "banking_techniques": len(self.get_banking_relevant_techniques()),
            "banking_groups": len(self.get_banking_threat_groups()),
            "storage_location": str(self.STORAGE_DIR),
            "files": {
                "techniques": str(self.TECHNIQUES_FILE),
                "tactics": str(self.TACTICS_FILE),
                "groups": str(self.GROUPS_FILE),
                "cache_info": str(self.CACHE_INFO_FILE)
            }
        }
