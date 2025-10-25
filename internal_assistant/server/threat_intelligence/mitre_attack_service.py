"""MITRE ATT&CK Integration Service for Internal Assistant."""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

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
    subtechniques: list[str]
    platforms: list[str]
    data_sources: list[str]
    detection: str | None
    mitigation: str | None
    url: str


@dataclass
class AttackTactic:
    """Represents a MITRE ATT&CK tactic."""

    tactic_id: str
    name: str
    description: str
    techniques: list[str]
    url: str


@dataclass
class ThreatGroup:
    """Represents a MITRE ATT&CK threat group."""

    group_id: str
    name: str
    description: str
    aliases: list[str]
    techniques: list[str]
    targets: list[str]
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

    # Sector-specific threat groups and techniques
    SECTOR_THREAT_GROUPS = {
        "Financial": [
            "APT29",
            "APT28",
            "Lazarus Group",
            "Carbanak",
            "Cobalt Group",
            "FIN7",
            "FIN8",
            "FIN9",
            "LAPSUS$",
            "Conti",
            "REvil",
        ],
        "Government": [
            "APT29",
            "APT28",
            "APT1",
            "APT10",
            "APT19",
            "APT38",
            "Turla",
            "Equation",
            "DarkHydrus",
            "Ke3chang",
            "Naikon",
        ],
        "Healthcare": [
            "APT41",
            "FIN7",
            "Wizard Spider",
            "Conti",
            "REvil",
            "LAPSUS$",
            "DarkSide",
            "Ryuk",
            "Maze",
            "SamSam",
        ],
        "Energy": [
            "Dragonfly",
            "Energetic Bear",
            "APT33",
            "APT34",
            "APT38",
            "HEXANE",
            "Sandworm",
            "BlackEnergy",
            "Industroyer",
        ],
        "Technology": [
            "APT41",
            "APT10",
            "Lazarus Group",
            "LAPSUS$",
            "APT29",
            "APT1",
            "Winnti Group",
            "Ke3chang",
            "menuPass",
            "Stone Panda",
        ],
        "Retail": [
            "FIN7",
            "FIN8",
            "Carbanak",
            "REvil",
            "Conti",
            "Wizard Spider",
            "Maze",
            "NetWalker",
        ],
        "Manufacturing": [
            "APT41",
            "Dragonfly",
            "APT10",
            "Wizard Spider",
            "Sandworm",
            "BlackEnergy",
            "Industroyer",
        ],
    }

    # Legacy support (default to Financial)
    TARGET_THREAT_GROUPS = SECTOR_THREAT_GROUPS["Financial"]

    # Common techniques across sectors (core attack patterns)
    COMMON_TECHNIQUES = [
        "T1078.004",
        "T1078.002",
        "T1566.001",
        "T1566.002",  # Initial Access
        "T1059.001",
        "T1059.003",
        "T1105",  # Execution
        "T1083",
        "T1082",
        "T1018",
        "T1057",  # Discovery
        "T1041",
        "T1048.003",
        "T1071.001",  # Exfiltration
    ]

    # Sector-specific technique focus
    SECTOR_TECHNIQUES = {
        "Financial": COMMON_TECHNIQUES
        + [
            "T1213",
            "T1005",
            "T1074.001",
            "T1560.001",  # Data Collection (financial records)
            "T1087.002",
            "T1087.001",  # Account Discovery
            "T1071.002",
            "T1071.003",  # Application Layer Protocol
        ],
        "Government": COMMON_TECHNIQUES
        + [
            "T1070.004",
            "T1027",
            "T1140",  # Defense Evasion (cover tracks)
            "T1482",
            "T1018",
            "T1016",  # Network Discovery
            "T1021.001",
            "T1021.004",  # Remote Services (RDP, SSH)
        ],
        "Healthcare": COMMON_TECHNIQUES
        + [
            "T1486",
            "T1490",
            "T1489",  # Impact (ransomware, data destruction)
            "T1213",
            "T1005",
            "T1039",  # Data from Repositories (patient records)
            "T1562.001",  # Impair Defenses
        ],
        "Energy": COMMON_TECHNIQUES
        + [
            "T1542",
            "T1495",
            "T1200",  # ICS/SCADA attacks
            "T1018",
            "T1046",
            "T1082",  # Network/System Discovery
            "T1489",
            "T1490",  # Service Stop, Inhibit System Recovery
        ],
        "Technology": COMMON_TECHNIQUES
        + [
            "T1195",
            "T1199",
            "T1078.004",  # Supply Chain, Cloud Accounts
            "T1213",
            "T1039",
            "T1005",  # Data Collection (IP theft)
            "T1071.001",
            "T1071.004",  # Web Protocols, DNS
        ],
        "Retail": COMMON_TECHNIQUES
        + [
            "T1213",
            "T1005",
            "T1560.001",  # Data Collection (POS, customer data)
            "T1486",
            "T1490",  # Ransomware
            "T1087.002",
            "T1087.001",  # Account Discovery
        ],
        "Manufacturing": COMMON_TECHNIQUES
        + [
            "T1542",
            "T1200",
            "T1018",  # ICS/Network targeting
            "T1486",
            "T1490",
            "T1489",  # Production disruption
            "T1213",
            "T1005",  # Data Collection (trade secrets)
        ],
    }

    # Legacy support (default to Financial)
    TARGET_TECHNIQUES = SECTOR_TECHNIQUES["Financial"]

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None
        self._techniques_cache: dict[str, AttackTechnique] = {}
        self._tactics_cache: dict[str, AttackTactic] = {}
        self._groups_cache: dict[str, ThreatGroup] = {}
        self._last_refresh: datetime | None = None

        # Ensure storage directory exists
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        # Load cached data from disk if available
        self._load_cached_data()

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            try:
                await self._session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
            finally:
                self._session = None

    async def fetch_techniques(
        self, domain: AttackDomain = AttackDomain.ENTERPRISE
    ) -> list[AttackTechnique]:
        """Fetch MITRE ATT&CK techniques."""
        if not self._session:
            raise RuntimeError("Service must be used within async context manager")

        try:
            url = f"{self.BASE_URL}techniques/{domain.value}/"
            async with self._session.get(url) as response:
                if response.status != 200:
                    logger.warning(
                        f"Failed to fetch techniques: HTTP {response.status}"
                    )
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
                            url=item.get("url", ""),
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

    async def fetch_tactics(
        self, domain: AttackDomain = AttackDomain.ENTERPRISE
    ) -> list[AttackTactic]:
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
                            url=item.get("url", ""),
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

    async def fetch_threat_groups(
        self, domain: AttackDomain = AttackDomain.ENTERPRISE
    ) -> list[ThreatGroup]:
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
                            url=item.get("url", ""),
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

    def get_sector_relevant_techniques(
        self, sector: str = "Financial"
    ) -> list[AttackTechnique]:
        """Get techniques relevant to the specified sector.

        Args:
            sector: Sector name (Financial, Government, Healthcare, Energy, Technology, Retail, Manufacturing)

        Returns:
            List of relevant attack techniques for the sector
        """
        relevant_techniques = []
        sector_techniques = self.SECTOR_TECHNIQUES.get(sector, self.TARGET_TECHNIQUES)

        for technique_id in sector_techniques:
            if technique_id in self._techniques_cache:
                relevant_techniques.append(self._techniques_cache[technique_id])

        return relevant_techniques

    def get_sector_threat_groups(self, sector: str = "Financial") -> list[ThreatGroup]:
        """Get threat groups targeting the specified sector.

        Args:
            sector: Sector name (Financial, Government, Healthcare, Energy, Technology, Retail, Manufacturing)

        Returns:
            List of threat groups targeting the sector
        """
        relevant_groups = []
        sector_groups = self.SECTOR_THREAT_GROUPS.get(sector, self.TARGET_THREAT_GROUPS)

        for group in self._groups_cache.values():
            if any(alias in sector_groups for alias in group.aliases):
                relevant_groups.append(group)

        return relevant_groups

    def get_available_sectors(self) -> list[str]:
        """Get list of available sectors for filtering.

        Returns:
            List of sector names
        """
        return list(self.SECTOR_THREAT_GROUPS.keys())

    def search_techniques(self, query: str) -> list[AttackTechnique]:
        """Search techniques by name or description."""
        results = []
        query_lower = query.lower()

        for technique in self._techniques_cache.values():
            if (
                query_lower in technique.name.lower()
                or query_lower in technique.description.lower()
            ):
                results.append(technique)

        return results

    def get_technique_by_id(self, technique_id: str) -> AttackTechnique | None:
        """Get technique by ID."""
        return self._techniques_cache.get(technique_id)

    def get_tactic_by_id(self, tactic_id: str) -> AttackTactic | None:
        """Get tactic by ID."""
        return self._tactics_cache.get(tactic_id)

    def get_group_by_id(self, group_id: str) -> ThreatGroup | None:
        """Get threat group by ID."""
        return self._groups_cache.get(group_id)

    async def refresh_data(self) -> bool:
        """Refresh all MITRE ATT&CK data."""
        try:
            await self.fetch_techniques()
            await self.fetch_tactics()
            await self.fetch_threat_groups()
            self._last_refresh = datetime.now(UTC)

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
                with open(self.TECHNIQUES_FILE) as f:
                    data = json.load(f)
                    for tech_data in data.values():
                        technique = AttackTechnique(**tech_data)
                        self._techniques_cache[technique.technique_id] = technique
                logger.info(
                    f"Loaded {len(self._techniques_cache)} techniques from cache"
                )

            # Load tactics
            if self.TACTICS_FILE.exists():
                with open(self.TACTICS_FILE) as f:
                    data = json.load(f)
                    for tactic_data in data.values():
                        tactic = AttackTactic(**tactic_data)
                        self._tactics_cache[tactic.tactic_id] = tactic
                logger.info(f"Loaded {len(self._tactics_cache)} tactics from cache")

            # Load groups
            if self.GROUPS_FILE.exists():
                with open(self.GROUPS_FILE) as f:
                    data = json.load(f)
                    for group_data in data.values():
                        group = ThreatGroup(**group_data)
                        self._groups_cache[group.group_id] = group
                logger.info(f"Loaded {len(self._groups_cache)} groups from cache")

            # Load cache info
            if self.CACHE_INFO_FILE.exists():
                with open(self.CACHE_INFO_FILE) as f:
                    cache_info = json.load(f)
                    if cache_info.get("last_refresh"):
                        self._last_refresh = datetime.fromisoformat(
                            cache_info["last_refresh"]
                        )

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
            with open(self.TECHNIQUES_FILE, "w") as f:
                json.dump(techniques_data, f, indent=2)

            # Save tactics
            tactics_data = {
                tactic_id: asdict(tactic)
                for tactic_id, tactic in self._tactics_cache.items()
            }
            with open(self.TACTICS_FILE, "w") as f:
                json.dump(tactics_data, f, indent=2)

            # Save groups
            groups_data = {
                group_id: asdict(group)
                for group_id, group in self._groups_cache.items()
            }
            with open(self.GROUPS_FILE, "w") as f:
                json.dump(groups_data, f, indent=2)

            # Save cache info
            cache_info = self.get_cache_info()
            with open(self.CACHE_INFO_FILE, "w") as f:
                json.dump(cache_info, f, indent=2)

            logger.info("MITRE ATT&CK data saved to disk")

        except Exception as e:
            logger.error(f"Error saving cached data: {e}")

    def get_cache_info(self) -> dict[str, Any]:
        """Get cache information."""
        return {
            "techniques_count": len(self._techniques_cache),
            "tactics_count": len(self._tactics_cache),
            "groups_count": len(self._groups_cache),
            "last_refresh": (
                self._last_refresh.isoformat() if self._last_refresh else None
            ),
            "sector_techniques": len(self.get_sector_relevant_techniques()),
            "sector_groups": len(self.get_sector_threat_groups()),
            "storage_location": str(self.STORAGE_DIR),
            "files": {
                "techniques": str(self.TECHNIQUES_FILE),
                "tactics": str(self.TACTICS_FILE),
                "groups": str(self.GROUPS_FILE),
                "cache_info": str(self.CACHE_INFO_FILE),
            },
        }
