"""Threat Intelligence Analysis Engine for Internal Assistant."""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(Enum):
    MALWARE = "malware"
    PHISHING = "phishing"
    RANSOMWARE = "ransomware"
    APT = "apt"
    VULNERABILITY = "vulnerability"
    SOCIAL_ENGINEERING = "social_engineering"


@dataclass
class ThreatIndicator:
    """Represents a cyber threat indicator."""

    indicator: str
    threat_type: ThreatType
    threat_level: ThreatLevel
    description: str
    source: str
    timestamp: datetime
    ioc_type: str  # IP, domain, hash, etc.
    confidence: float


@dataclass
class SecurityRecommendation:
    """Security recommendation based on threat analysis."""

    title: str
    description: str
    priority: ThreatLevel
    action_items: List[str]
    affected_systems: List[str]
    estimated_effort: str
    compliance_impact: List[str]


class ThreatIntelligenceAnalyzer:
    """Analyzes cyber threat feeds and provides security recommendations with MITRE ATT&CK integration."""

    def __init__(self):
        self.threat_patterns = {
            ThreatType.MALWARE: [
                r"malware",
                r"trojan",
                r"virus",
                r"worm",
                r"backdoor",
                r"keylogger",
                r"spyware",
                r"rootkit",
            ],
            ThreatType.PHISHING: [
                r"phishing",
                r"spear.?phishing",
                r"whaling",
                r"vishing",
                r"smishing",
                r"credential.?harvesting",
            ],
            ThreatType.RANSOMWARE: [
                r"ransomware",
                r"crypto.?locker",
                r"file.?encryption",
                r"bitcoin.?demand",
                r"decrypt.?key",
            ],
            ThreatType.APT: [
                r"apt",
                r"advanced.?persistent.?threat",
                r"nation.?state",
                r"cyber.?espionage",
                r"zero.?day",
            ],
            ThreatType.VULNERABILITY: [
                r"cve",
                r"vulnerability",
                r"exploit",
                r"patch",
                r"update",
                r"security.?flaw",
                r"buffer.?overflow",
            ],
        }

        self.sector_keywords = [
            "security",
            "cyber",
            "threat",
            "vulnerability",
            "breach",
            "attack",
            "malware",
            "ransomware",
            "incident",
            "compromise",
        ]

        # MITRE ATT&CK technique patterns for enhanced detection
        self.mitre_technique_patterns = {
            "T1078": r"valid.?account|credential.?access|authentication",
            "T1566": r"phishing|spear.?phishing|social.?engineering",
            "T1071": r"command.?and.?control|c2|communication.?protocol",
            "T1105": r"ingress.?tool.?transfer|file.?download|malware.?download",
            "T1059": r"command.?scripting|powershell|bash|cmd",
            "T1083": r"file.?directory.?discovery|dir|ls|find",
            "T1082": r"system.?information|systeminfo|uname|hostname",
            "T1018": r"remote.?system.?discovery|network.?scan|ping|nmap",
            "T1057": r"process.?discovery|tasklist|ps|process.?enumeration",
            "T1049": r"network.?connection|netstat|connection.?discovery",
            "T1016": r"network.?configuration|ipconfig|ifconfig|network.?settings",
            "T1007": r"system.?service|service.?discovery|service.?enumeration",
            "T1482": r"domain.?trust|trust.?discovery|domain.?enumeration",
            "T1087": r"account.?discovery|user.?enumeration|account.?enumeration",
            "T1010": r"application.?window|window.?discovery|gui.?discovery",
            "T1213": r"data.?repository|database|information.?repository",
            "T1005": r"local.?data|file.?system|local.?information",
            "T1039": r"network.?shared|shared.?drive|network.?storage",
            "T1025": r"removable.?media|usb|external.?storage|removable.?drive",
            "T1074": r"data.?staging|staging.?area|data.?collection",
            "T1560": r"archive.?data|compression|archive.?utility",
            "T1041": r"exfiltration|c2.?channel|data.?exfiltration",
            "T1048": r"alternative.?protocol|exfiltration.?protocol",
            "T1011": r"network.?medium|usb.?exfiltration|physical.?medium",
            "T1052": r"physical.?medium|usb|network.?medium|physical.?exfiltration",
            "T1090": r"proxy|multi.?hop|domain.?fronting|proxy.?chain",
            "T1219": r"remote.?access|remote.?desktop|vnc|teamviewer",
            "T1133": r"external.?remote|vpn|remote.?service|external.?access",
            "T1021": r"remote.?service|rdp|smb|ssh|remote.?desktop",
            "T1078": r"valid.?account|default.?account|domain.?account|cloud.?account",
            "T1136": r"create.?account|account.?creation|user.?creation",
        }

    def extract_mitre_techniques_from_feed_item(
        self, feed_item: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Extract relevant MITRE ATT&CK techniques from a single feed item.

        This method analyzes the title and summary of a feed item and identifies
        relevant MITRE techniques based on pattern matching.

        Args:
            feed_item: Dictionary containing 'title' and 'summary' keys

        Returns:
            List of dictionaries with technique_id, confidence, and matched_text

        Example:
            >>> analyzer = ThreatIntelligenceAnalyzer()
            >>> feed_item = {
            ...     "title": "New Phishing Campaign Targets Financial Institutions",
            ...     "summary": "Spearphishing attacks using malicious attachments..."
            ... }
            >>> techniques = analyzer.extract_mitre_techniques_from_feed_item(feed_item)
            >>> # Returns: [{"technique_id": "T1566", "confidence": 0.9, ...}]
        """
        content = f"{feed_item.get('title', '')} {feed_item.get('summary', '')}".lower()
        matched_techniques = []

        # Scan content for MITRE technique patterns
        for technique_id, pattern in self.mitre_technique_patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                # Calculate confidence based on match quality
                matched_text = match.group(0)
                confidence = self._calculate_technique_confidence(
                    content, pattern, matched_text
                )

                matched_techniques.append({
                    "technique_id": technique_id,
                    "confidence": confidence,
                    "matched_text": matched_text,
                    "pattern": pattern,
                })

        # Sort by confidence (highest first)
        matched_techniques.sort(key=lambda x: x["confidence"], reverse=True)

        return matched_techniques

    def _calculate_technique_confidence(
        self, content: str, pattern: str, matched_text: str
    ) -> float:
        """Calculate confidence score for MITRE technique detection."""
        confidence = 0.6  # Base confidence for pattern match

        # Multiple occurrences increase confidence
        match_count = len(re.findall(pattern, content, re.IGNORECASE))
        if match_count > 1:
            confidence += min(match_count * 0.1, 0.2)

        # Exact match of key terms (not partial) increases confidence
        if matched_text in ["phishing", "ransomware", "malware", "vulnerability", "exploit"]:
            confidence += 0.1

        # Presence of security keywords increases confidence
        if any(keyword in content for keyword in self.sector_keywords):
            confidence += 0.1

        return min(confidence, 1.0)

    def build_attack_chain(self, detected_techniques: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build attack chain from detected techniques, ordering by kill chain phase.

        Args:
            detected_techniques: List of detected techniques with IDs and confidence

        Returns:
            Dictionary with ordered phases and techniques
        """
        # MITRE kill chain phase mapping
        KILL_CHAIN_PHASES = {
            # Initial Access
            'T1566': {'phase': 'Initial Access', 'order': 1, 'name': 'Phishing'},
            'T1190': {'phase': 'Initial Access', 'order': 1, 'name': 'Exploit Public-Facing Application'},
            'T1078': {'phase': 'Initial Access', 'order': 1, 'name': 'Valid Accounts'},
            'T1133': {'phase': 'Initial Access', 'order': 1, 'name': 'External Remote Services'},

            # Execution
            'T1059': {'phase': 'Execution', 'order': 2, 'name': 'Command and Scripting Interpreter'},
            'T1203': {'phase': 'Execution', 'order': 2, 'name': 'Exploitation for Client Execution'},
            'T1053': {'phase': 'Execution', 'order': 2, 'name': 'Scheduled Task/Job'},

            # Persistence
            'T1098': {'phase': 'Persistence', 'order': 3, 'name': 'Account Manipulation'},
            'T1136': {'phase': 'Persistence', 'order': 3, 'name': 'Create Account'},
            'T1547': {'phase': 'Persistence', 'order': 3, 'name': 'Boot or Logon Autostart Execution'},

            # Credential Access
            'T1003': {'phase': 'Credential Access', 'order': 4, 'name': 'OS Credential Dumping'},
            'T1110': {'phase': 'Credential Access', 'order': 4, 'name': 'Brute Force'},
            'T1528': {'phase': 'Credential Access', 'order': 4, 'name': 'Steal Application Access Token'},

            # Lateral Movement
            'T1021': {'phase': 'Lateral Movement', 'order': 5, 'name': 'Remote Services'},
            'T1091': {'phase': 'Lateral Movement', 'order': 5, 'name': 'Replication Through Removable Media'},
            'T1080': {'phase': 'Lateral Movement', 'order': 5, 'name': 'Taint Shared Content'},

            # Impact
            'T1486': {'phase': 'Impact', 'order': 6, 'name': 'Data Encrypted for Impact'},
            'T1490': {'phase': 'Impact', 'order': 6, 'name': 'Inhibit System Recovery'},
            'T1499': {'phase': 'Impact', 'order': 6, 'name': 'Endpoint Denial of Service'},
        }

        # Group techniques by phase
        phases = {}
        for tech in detected_techniques:
            tech_id = tech.get('technique_id', '')
            base_tech_id = tech_id.split('.')[0]  # Handle sub-techniques (e.g., T1566.001 -> T1566)

            if base_tech_id in KILL_CHAIN_PHASES:
                phase_info = KILL_CHAIN_PHASES[base_tech_id]
                phase_name = phase_info['phase']
                phase_order = phase_info['order']

                if phase_name not in phases:
                    phases[phase_name] = {
                        'order': phase_order,
                        'techniques': []
                    }

                phases[phase_name]['techniques'].append({
                    'technique_id': tech_id,
                    'name': tech.get('matched_text', phase_info['name']),
                    'confidence': tech.get('confidence', 0.0),
                })

        # Sort phases by order
        sorted_phases = sorted(phases.items(), key=lambda x: x[1]['order'])

        return {
            'phases': sorted_phases,
            'total_phases': len(sorted_phases),
            'is_complete_chain': len(sorted_phases) >= 3,  # 3+ phases = likely complete attack
        }

    def get_mitigations_for_technique(self, technique_id: str) -> List[Dict[str, str]]:
        """
        Get MITRE mitigations for a technique.

        Args:
            technique_id: MITRE technique ID (e.g., "T1566")

        Returns:
            List of mitigation dictionaries with id and name
        """
        # Common mitigations mapping (hardcoded for reliability)
        COMMON_MITIGATIONS = {
            'T1566': [
                {'id': 'M1049', 'name': 'Antivirus/Antimalware'},
                {'id': 'M1031', 'name': 'Network Intrusion Prevention'},
                {'id': 'M1017', 'name': 'User Training'},
                {'id': 'M1021', 'name': 'Restrict Web-Based Content'},
            ],
            'T1059': [
                {'id': 'M1042', 'name': 'Disable or Remove Feature'},
                {'id': 'M1038', 'name': 'Execution Prevention'},
                {'id': 'M1026', 'name': 'Privileged Account Management'},
            ],
            'T1003': [
                {'id': 'M1028', 'name': 'Operating System Configuration'},
                {'id': 'M1043', 'name': 'Credential Access Protection'},
                {'id': 'M1027', 'name': 'Password Policies'},
                {'id': 'M1026', 'name': 'Privileged Account Management'},
            ],
            'T1021': [
                {'id': 'M1035', 'name': 'Limit Access to Resource Over Network'},
                {'id': 'M1032', 'name': 'Multi-factor Authentication'},
                {'id': 'M1030', 'name': 'Network Segmentation'},
                {'id': 'M1018', 'name': 'User Account Management'},
            ],
            'T1486': [
                {'id': 'M1053', 'name': 'Data Backup'},
                {'id': 'M1040', 'name': 'Behavior Prevention on Endpoint'},
                {'id': 'M1022', 'name': 'Restrict File and Directory Permissions'},
            ],
            'T1490': [
                {'id': 'M1053', 'name': 'Data Backup'},
                {'id': 'M1028', 'name': 'Operating System Configuration'},
                {'id': 'M1026', 'name': 'Privileged Account Management'},
            ],
            'T1078': [
                {'id': 'M1027', 'name': 'Password Policies'},
                {'id': 'M1032', 'name': 'Multi-factor Authentication'},
                {'id': 'M1026', 'name': 'Privileged Account Management'},
                {'id': 'M1018', 'name': 'User Account Management'},
            ],
            'T1190': [
                {'id': 'M1048', 'name': 'Application Isolation and Sandboxing'},
                {'id': 'M1030', 'name': 'Network Segmentation'},
                {'id': 'M1016', 'name': 'Vulnerability Scanning'},
                {'id': 'M1050', 'name': 'Exploit Protection'},
            ],
        }

        # Use common mitigations
        base_tech_id = technique_id.split('.')[0]
        mitigations = COMMON_MITIGATIONS.get(base_tech_id, [])

        if not mitigations:
            logger.debug(f"No mitigations found for technique {technique_id}")
            # Return generic mitigations as fallback
            mitigations = [
                {'id': 'M1051', 'name': 'Update Software'},
                {'id': 'M1047', 'name': 'Audit'},
            ]

        return mitigations

    def analyze_feed_content(self, feed_items: List[Dict]) -> List[ThreatIndicator]:
        """Analyze RSS feed content for cyber threats."""
        threats = []

        for item in feed_items:
            content = f"{item.get('title', '')} {item.get('summary', '')}".lower()

            # Check for threat patterns
            for threat_type, patterns in self.threat_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        threat_level = self._assess_threat_level(content, threat_type)

                        # Extract indicators
                        indicators = self._extract_indicators(content)

                        for indicator in indicators:
                            threat = ThreatIndicator(
                                indicator=indicator,
                                threat_type=threat_type,
                                threat_level=threat_level,
                                description=item.get("summary", "")[:200],
                                source=item.get("source", "Unknown"),
                                timestamp=item.get("published", datetime.now()),
                                ioc_type=self._classify_ioc(indicator),
                                confidence=self._calculate_confidence(
                                    content, threat_type
                                ),
                            )
                            threats.append(threat)

        return threats

    def _assess_threat_level(
        self, content: str, threat_type: ThreatType
    ) -> ThreatLevel:
        """Assess the threat level based on content analysis."""
        # Sector-specific threats get higher priority
        sector_relevance = any(keyword in content for keyword in self.sector_keywords)

        # Critical keywords
        critical_keywords = ["critical", "emergency", "immediate", "active", "ongoing"]
        is_critical = any(keyword in content for keyword in critical_keywords)

        if is_critical and sector_relevance:
            return ThreatLevel.CRITICAL
        elif is_critical:
            return ThreatLevel.HIGH
        elif sector_relevance:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW

    def _extract_indicators(self, content: str) -> List[str]:
        """Extract threat indicators from content."""
        indicators = []

        # IP addresses
        ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
        indicators.extend(re.findall(ip_pattern, content))

        # Domains
        domain_pattern = (
            r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b"
        )
        indicators.extend(re.findall(domain_pattern, content))

        # Hashes (MD5, SHA1, SHA256)
        hash_patterns = [
            r"\b[a-fA-F0-9]{32}\b",  # MD5
            r"\b[a-fA-F0-9]{40}\b",  # SHA1
            r"\b[a-fA-F0-9]{64}\b",  # SHA256
        ]
        for pattern in hash_patterns:
            indicators.extend(re.findall(pattern, content))

        return list(set(indicators))  # Remove duplicates

    def _classify_ioc(self, indicator: str) -> str:
        """Classify the type of indicator of compromise."""
        if re.match(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", indicator):
            return "IP"
        elif re.match(
            r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b",
            indicator,
        ):
            return "Domain"
        elif re.match(r"\b[a-fA-F0-9]{32,64}\b", indicator):
            return "Hash"
        else:
            return "Unknown"

    def _calculate_confidence(self, content: str, threat_type: ThreatType) -> float:
        """Calculate confidence score for threat detection."""
        confidence = 0.5  # Base confidence

        # Multiple threat keywords increase confidence
        threat_keywords = sum(
            1
            for pattern in self.threat_patterns[threat_type]
            if re.search(pattern, content, re.IGNORECASE)
        )
        confidence += min(threat_keywords * 0.2, 0.3)

        # Financial sector relevance increases confidence
        banking_keywords = [
            "banking",
            "financial",
            "bank",
            "finance",
            "fintech",
            "payment",
        ]
        if any(keyword in content for keyword in banking_keywords):
            confidence += 0.2

        return min(confidence, 1.0)

    def get_mitre_data(self) -> Dict[str, Any]:
        """Get MITRE ATT&CK data from API."""
        try:
            import aiohttp
            import asyncio

            # For now, return sample data since we need async context
            # In a real implementation, this would call the MITRE ATT&CK API
            return {
                "techniques": [
                    # Initial Access Techniques
                    {
                        "technique_id": "T1078.004",
                        "name": "Valid Accounts: Cloud Accounts",
                        "description": "Adversaries may obtain and abuse credentials of existing accounts as a means of gaining Initial Access, Persistence, Privilege Escalation, or Defense Evasion.",
                        "tactic": "Initial Access",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1078/004/",
                    },
                    {
                        "technique_id": "T1566.001",
                        "name": "Phishing: Spearphishing Attachment",
                        "description": "Adversaries may send spearphishing emails with a malicious attachment in an attempt to gain access to victim systems.",
                        "tactic": "Initial Access",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1566/001/",
                    },
                    {
                        "technique_id": "T1190",
                        "name": "Exploit Public-Facing Application",
                        "description": "Adversaries may attempt to take advantage of a weakness in an Internet-facing computer system or program.",
                        "tactic": "Initial Access",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1190/",
                    },
                    # Execution Techniques
                    {
                        "technique_id": "T1059.001",
                        "name": "Command and Scripting Interpreter: PowerShell",
                        "description": "Adversaries may abuse PowerShell commands and scripts for execution. PowerShell is a powerful interactive command-line interface and scripting environment.",
                        "tactic": "Execution",
                        "platforms": ["Windows"],
                        "url": "https://attack.mitre.org/techniques/T1059/001/",
                    },
                    {
                        "technique_id": "T1059.003",
                        "name": "Command and Scripting Interpreter: Windows Command Shell",
                        "description": "Adversaries may abuse the Windows command shell for execution. The Windows command shell can control the system and execute various commands.",
                        "tactic": "Execution",
                        "platforms": ["Windows"],
                        "url": "https://attack.mitre.org/techniques/T1059/003/",
                    },
                    {
                        "technique_id": "T1053.005",
                        "name": "Scheduled Task/Job: Scheduled Task",
                        "description": "Adversaries may abuse the Windows Task Scheduler to perform task scheduling for initial or recurring execution of malicious code.",
                        "tactic": "Execution",
                        "platforms": ["Windows"],
                        "url": "https://attack.mitre.org/techniques/T1053/005/",
                    },
                    # Persistence Techniques
                    {
                        "technique_id": "T1547.001",
                        "name": "Boot or Logon Autostart Execution: Registry Run Keys / Startup Folder",
                        "description": "Adversaries may configure system settings to automatically execute a program during system boot or logon.",
                        "tactic": "Persistence",
                        "platforms": ["Windows"],
                        "url": "https://attack.mitre.org/techniques/T1547/001/",
                    },
                    {
                        "technique_id": "T1053.005",
                        "name": "Scheduled Task/Job: Scheduled Task",
                        "description": "Adversaries may abuse the Windows Task Scheduler to perform task scheduling for initial or recurring execution of malicious code.",
                        "tactic": "Persistence",
                        "platforms": ["Windows"],
                        "url": "https://attack.mitre.org/techniques/T1053/005/",
                    },
                    # Privilege Escalation Techniques
                    {
                        "technique_id": "T1548.002",
                        "name": "Abuse Elevation Control Mechanism: Bypass User Account Control",
                        "description": "Adversaries may bypass UAC mechanisms to elevate process privileges on system.",
                        "tactic": "Privilege Escalation",
                        "platforms": ["Windows"],
                        "url": "https://attack.mitre.org/techniques/T1548/002/",
                    },
                    {
                        "technique_id": "T1068",
                        "name": "Exploitation for Privilege Escalation",
                        "description": "Adversaries may exploit software vulnerabilities in an attempt to collect privileges.",
                        "tactic": "Privilege Escalation",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1068/",
                    },
                    # Defense Evasion Techniques
                    {
                        "technique_id": "T1562.001",
                        "name": "Impair Defenses: Disable or Modify Tools",
                        "description": "Adversaries may modify and/or disable security tools to avoid possible detection of their malware/tools and activities.",
                        "tactic": "Defense Evasion",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1562/001/",
                    },
                    {
                        "technique_id": "T1070.004",
                        "name": "Indicator Removal on Host: File Deletion",
                        "description": "Adversaries may delete files left behind by the actions of their intrusion activity.",
                        "tactic": "Defense Evasion",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1070/004/",
                    },
                    # Credential Access Techniques
                    {
                        "technique_id": "T1003.001",
                        "name": "OS Credential Dumping: LSASS Memory",
                        "description": "Adversaries may attempt to access credential material stored in the process memory of the Local Security Authority Subsystem Service (LSASS).",
                        "tactic": "Credential Access",
                        "platforms": ["Windows"],
                        "url": "https://attack.mitre.org/techniques/T1003/001/",
                    },
                    {
                        "technique_id": "T1110.001",
                        "name": "Brute Force: Password Guessing",
                        "description": "Adversaries may use brute force techniques to gain access to accounts when passwords are unknown or when password hashes are obtained.",
                        "tactic": "Credential Access",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1110/001/",
                    },
                    # Discovery Techniques
                    {
                        "technique_id": "T1083",
                        "name": "File and Directory Discovery",
                        "description": "Adversaries may enumerate files and directories or may search in specific locations of a host or network share for certain information.",
                        "tactic": "Discovery",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1083/",
                    },
                    {
                        "technique_id": "T1082",
                        "name": "System Information Discovery",
                        "description": "An adversary may attempt to get detailed information about the operating system and hardware, including version, patches, hotfixes, service packs, and architecture.",
                        "tactic": "Discovery",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1082/",
                    },
                    {
                        "technique_id": "T1018",
                        "name": "Remote System Discovery",
                        "description": "Adversaries may attempt to get a listing of other systems by IP address, hostname, or other logical identifiers on a network.",
                        "tactic": "Discovery",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1018/",
                    },
                    # Lateral Movement Techniques
                    {
                        "technique_id": "T1021.001",
                        "name": "Remote Services: Remote Desktop Protocol",
                        "description": "Adversaries may use Valid Accounts to log into a computer using the Remote Desktop Protocol (RDP).",
                        "tactic": "Lateral Movement",
                        "platforms": ["Windows"],
                        "url": "https://attack.mitre.org/techniques/T1021/001/",
                    },
                    {
                        "technique_id": "T1021.002",
                        "name": "Remote Services: SMB/Windows Admin Shares",
                        "description": "Adversaries may use Valid Accounts to interact with a remote network share using Server Message Block (SMB).",
                        "tactic": "Lateral Movement",
                        "platforms": ["Windows"],
                        "url": "https://attack.mitre.org/techniques/T1021/002/",
                    },
                    # Collection Techniques
                    {
                        "technique_id": "T1005",
                        "name": "Data from Local System",
                        "description": "Adversaries may search local system sources, such as file systems and configuration files or local databases, to find files of interest and sensitive data.",
                        "tactic": "Collection",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1005/",
                    },
                    {
                        "technique_id": "T1074.001",
                        "name": "Data Staged: Local Data Staging",
                        "description": "Adversaries may stage collected data in a central location or directory on the local system prior to Exfiltration.",
                        "tactic": "Collection",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1074/001/",
                    },
                    # Command & Control Techniques
                    {
                        "technique_id": "T1071.001",
                        "name": "Application Layer Protocol: Web Protocols",
                        "description": "Adversaries may communicate using application layer protocols associated with web traffic to avoid detection/network filtering by blending in with existing traffic.",
                        "tactic": "Command & Control",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1071/001/",
                    },
                    {
                        "technique_id": "T1071.004",
                        "name": "Application Layer Protocol: DNS",
                        "description": "Adversaries may communicate using the Domain Name System (DNS) application layer protocol to avoid detection/network filtering by blending in with existing traffic.",
                        "tactic": "Command & Control",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1071/004/",
                    },
                    # Exfiltration Techniques
                    {
                        "technique_id": "T1041",
                        "name": "Exfiltration Over C2 Channel",
                        "description": "Adversaries may steal data by exfiltrating it over an existing command and control channel.",
                        "tactic": "Exfiltration",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1041/",
                    },
                    {
                        "technique_id": "T1048.003",
                        "name": "Exfiltration Over Alternative Protocol: Exfiltration Over Unencrypted/Obfuscated Non-C2 Protocol",
                        "description": "Adversaries may steal data by exfiltrating it over an unencrypted or obfuscated non-C2 protocol instead of over an existing command and control channel.",
                        "tactic": "Exfiltration",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1048/003/",
                    },
                    # Impact Techniques
                    {
                        "technique_id": "T1486",
                        "name": "Data Encrypted for Impact",
                        "description": "Adversaries may encrypt data on target systems or on large numbers of systems in a network to interrupt availability to system and network resources.",
                        "tactic": "Impact",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1486/",
                    },
                    {
                        "technique_id": "T1490",
                        "name": "Inhibit System Recovery",
                        "description": "Adversaries may delete or remove built-in data and turn off services designed to aid in the recovery of a corrupted system.",
                        "tactic": "Impact",
                        "platforms": ["Windows", "Linux", "macOS"],
                        "url": "https://attack.mitre.org/techniques/T1490/",
                    },
                ],
                "groups": [
                    {
                        "group_id": "G0007",
                        "name": "APT29",
                        "description": "APT29 is a Russian cyber espionage group that has been active since at least 2008. The group has targeted government organizations and think tanks.",
                        "techniques": ["T1078", "T1566", "T1059"],
                        "targets": ["Financial institutions", "Government"],
                        "url": "https://attack.mitre.org/groups/G0007/",
                    },
                    {
                        "group_id": "G0032",
                        "name": "Lazarus Group",
                        "description": "Lazarus Group is a North Korean cyber threat group that has been active since at least 2009. The group has targeted financial institutions and cryptocurrency exchanges.",
                        "techniques": ["T1078", "T1566", "T1105"],
                        "targets": ["Banking", "Cryptocurrency"],
                        "url": "https://attack.mitre.org/groups/G0032/",
                    },
                    {
                        "group_id": "G0006",
                        "name": "APT28",
                        "description": "APT28 is a Russian cyber espionage group that has been active since at least 2007. The group has targeted government, military, and security organizations.",
                        "techniques": ["T1078", "T1566", "T1059", "T1083"],
                        "targets": ["Government", "Military", "Security"],
                        "url": "https://attack.mitre.org/groups/G0006/",
                    },
                    {
                        "group_id": "G0016",
                        "name": "APT-C-01",
                        "description": "APT-C-01 is a Chinese cyber espionage group that has been active since at least 2004. The group has targeted various industries including technology and government.",
                        "techniques": ["T1078", "T1566", "T1059", "T1083"],
                        "targets": ["Technology", "Government", "Healthcare"],
                        "url": "https://attack.mitre.org/groups/G0016/",
                    },
                    {
                        "group_id": "G0046",
                        "name": "APT-C-23",
                        "description": "APT-C-23 is a Palestinian cyber espionage group that has been active since at least 2017. The group has targeted various organizations in the Middle East.",
                        "techniques": ["T1078", "T1566", "T1059"],
                        "targets": ["Government", "Education", "Media"],
                        "url": "https://attack.mitre.org/groups/G0046/",
                    },
                    {
                        "group_id": "G0094",
                        "name": "APT-C-35",
                        "description": "APT-C-35 is an Iranian cyber espionage group that has been active since at least 2017. The group has targeted various industries and government entities.",
                        "techniques": ["T1078", "T1566", "T1059", "T1083"],
                        "targets": ["Government", "Technology", "Healthcare"],
                        "url": "https://attack.mitre.org/groups/G0094/",
                    },
                    {
                        "group_id": "G0126",
                        "name": "APT-C-36",
                        "description": "APT-C-36 is a Pakistani cyber espionage group that has been active since at least 2016. The group has targeted various organizations in South Asia.",
                        "techniques": ["T1078", "T1566", "T1059"],
                        "targets": ["Government", "Education", "Media"],
                        "url": "https://attack.mitre.org/groups/G0126/",
                    },
                    {
                        "group_id": "G0134",
                        "name": "APT-C-37",
                        "description": "APT-C-37 is a Vietnamese cyber espionage group that has been active since at least 2014. The group has targeted various organizations in Southeast Asia.",
                        "techniques": ["T1078", "T1566", "T1059", "T1083"],
                        "targets": ["Government", "Technology", "Education"],
                        "url": "https://attack.mitre.org/groups/G0134/",
                    },
                ],
            }
        except Exception as e:
            logger.error(f"Error getting MITRE data: {e}")
            return {}

    def get_domain_techniques(self, domain: str) -> list:
        """Get list of domain-relevant MITRE ATT&CK techniques."""
        domain_techniques = {
            "Financial Services": [
                "T1078.004",  # Valid Accounts: Cloud Accounts
                "T1078.002",  # Valid Accounts: Domain Accounts
                "T1566.001",  # Phishing: Spearphishing Attachment
                "T1566.002",  # Phishing: Spearphishing Link
                "T1071.001",  # Application Layer Protocol: Web Protocols
                "T1071.004",  # Application Layer Protocol: DNS
                "T1105",  # Ingress Tool Transfer
                "T1059.001",  # Command and Scripting Interpreter: PowerShell
                "T1059.003",  # Command and Scripting Interpreter: Windows Command Shell
                "T1083",  # File and Directory Discovery
                "T1082",  # System Information Discovery
                "T1018",  # Remote System Discovery
                "T1057",  # Process Discovery
                "T1049",  # System Network Connections Discovery
                "T1016",  # System Network Configuration Discovery
            ],
            "Healthcare": [
                "T1078.004",  # Valid Accounts: Cloud Accounts
                "T1566.001",  # Phishing: Spearphishing Attachment
                "T1071.001",  # Application Layer Protocol: Web Protocols
                "T1105",  # Ingress Tool Transfer
                "T1083",  # File and Directory Discovery
                "T1082",  # System Information Discovery
                "T1057",  # Process Discovery
                "T1049",  # System Network Connections Discovery
            ],
            "Government": [
                "T1078.002",  # Valid Accounts: Domain Accounts
                "T1566.001",  # Phishing: Spearphishing Attachment
                "T1071.001",  # Application Layer Protocol: Web Protocols
                "T1105",  # Ingress Tool Transfer
                "T1083",  # File and Directory Discovery
                "T1082",  # System Information Discovery
                "T1018",  # Remote System Discovery
                "T1057",  # Process Discovery
            ],
            "Technology": [
                "T1078.004",  # Valid Accounts: Cloud Accounts
                "T1566.001",  # Phishing: Spearphishing Attachment
                "T1071.001",  # Application Layer Protocol: Web Protocols
                "T1105",  # Ingress Tool Transfer
                "T1083",  # File and Directory Discovery
                "T1082",  # System Information Discovery
                "T1057",  # Process Discovery
            ],
        }
        return domain_techniques.get(domain, [])

    def generate_security_recommendations(
        self, threats: List[ThreatIndicator]
    ) -> List[SecurityRecommendation]:
        """Generate security recommendations based on threat analysis."""
        recommendations = []

        # Group threats by type
        threats_by_type = {}
        for threat in threats:
            if threat.threat_type not in threats_by_type:
                threats_by_type[threat.threat_type] = []
            threats_by_type[threat.threat_type].append(threat)

        # Generate recommendations for each threat type
        for threat_type, type_threats in threats_by_type.items():
            if not type_threats:
                continue

            # Find highest threat level
            max_level = max(threat.threat_level for threat in type_threats)

            recommendation = self._create_recommendation(
                threat_type, type_threats, max_level
            )
            recommendations.append(recommendation)

        return recommendations

    def _create_recommendation(
        self,
        threat_type: ThreatType,
        threats: List[ThreatIndicator],
        threat_level: ThreatLevel,
    ) -> SecurityRecommendation:
        """Create a specific security recommendation."""

        recommendations_map = {
            ThreatType.MALWARE: {
                "title": "Malware Threat Detection - Immediate Action Required",
                "description": f"Detected {len(threats)} malware indicators. Implement enhanced endpoint protection.",
                "action_items": [
                    "Update antivirus signatures immediately",
                    "Scan all endpoints for malware",
                    "Review and update firewall rules",
                    "Implement application whitelisting",
                    "Conduct security awareness training",
                ],
                "affected_systems": ["Endpoints", "Servers", "Network"],
                "estimated_effort": "4-6 hours",
                "compliance_impact": ["BSA/AML", "GLBA", "SOX"],
            },
            ThreatType.PHISHING: {
                "title": "Phishing Campaign Alert - Employee Training Required",
                "description": f"Identified {len(threats)} phishing indicators targeting financial institutions.",
                "action_items": [
                    "Send phishing awareness alerts to all employees",
                    "Review email security settings",
                    "Implement multi-factor authentication",
                    "Conduct phishing simulation exercises",
                    "Update email filtering rules",
                ],
                "affected_systems": ["Email Systems", "User Accounts", "Training"],
                "estimated_effort": "2-4 hours",
                "compliance_impact": ["BSA/AML", "GLBA", "FFIEC"],
            },
            ThreatType.RANSOMWARE: {
                "title": "Ransomware Threat - Critical Backup Review Required",
                "description": f"Detected {len(threats)} ransomware indicators. Verify backup integrity immediately.",
                "action_items": [
                    "Verify all backup systems are operational",
                    "Test disaster recovery procedures",
                    "Review network segmentation",
                    "Implement ransomware protection tools",
                    "Update incident response plan",
                ],
                "affected_systems": ["Backup Systems", "Network", "Endpoints"],
                "estimated_effort": "6-8 hours",
                "compliance_impact": ["BSA/AML", "GLBA", "SOX", "FFIEC"],
            },
            ThreatType.VULNERABILITY: {
                "title": "Critical Vulnerability Alert - Patch Management Required",
                "description": f"Identified {len(threats)} critical vulnerabilities requiring immediate patching.",
                "action_items": [
                    "Prioritize critical patches for immediate deployment",
                    "Review vulnerability management procedures",
                    "Conduct security assessments",
                    "Update patch management policies",
                    "Implement automated patch deployment",
                ],
                "affected_systems": ["All Systems", "Network Infrastructure"],
                "estimated_effort": "8-12 hours",
                "compliance_impact": ["GLBA", "SOX", "FFIEC"],
            },
        }

        config = recommendations_map.get(
            threat_type,
            {
                "title": f"{threat_type.value.title()} Threat Detected",
                "description": f"Detected {len(threats)} {threat_type.value} indicators.",
                "action_items": [
                    "Review security controls",
                    "Update incident response plan",
                ],
                "affected_systems": ["All Systems"],
                "estimated_effort": "2-4 hours",
                "compliance_impact": ["General Compliance"],
            },
        )

        return SecurityRecommendation(
            title=config["title"],
            description=config["description"],
            priority=threat_level,
            action_items=config["action_items"],
            affected_systems=config["affected_systems"],
            estimated_effort=config["estimated_effort"],
            compliance_impact=config["compliance_impact"],
        )
