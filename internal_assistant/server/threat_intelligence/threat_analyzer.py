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
                r"malware", r"trojan", r"virus", r"worm", r"backdoor",
                r"keylogger", r"spyware", r"rootkit"
            ],
            ThreatType.PHISHING: [
                r"phishing", r"spear.?phishing", r"whaling", r"vishing",
                r"smishing", r"credential.?harvesting"
            ],
            ThreatType.RANSOMWARE: [
                r"ransomware", r"crypto.?locker", r"file.?encryption",
                r"bitcoin.?demand", r"decrypt.?key"
            ],
            ThreatType.APT: [
                r"apt", r"advanced.?persistent.?threat", r"nation.?state",
                r"cyber.?espionage", r"zero.?day"
            ],
            ThreatType.VULNERABILITY: [
                r"cve", r"vulnerability", r"exploit", r"patch", r"update",
                r"security.?flaw", r"buffer.?overflow"
            ]
        }
        
        self.banking_keywords = [
            "banking", "financial", "payment", "transaction", "account",
            "credit", "debit", "swift", "ach", "wire", "transfer"
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
            "T1136": r"create.?account|account.?creation|user.?creation"
        }
    
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
                                description=item.get('summary', '')[:200],
                                source=item.get('source', 'Unknown'),
                                timestamp=item.get('published', datetime.now()),
                                ioc_type=self._classify_ioc(indicator),
                                confidence=self._calculate_confidence(content, threat_type)
                            )
                            threats.append(threat)
        
        return threats
    
    def _assess_threat_level(self, content: str, threat_type: ThreatType) -> ThreatLevel:
        """Assess the threat level based on content analysis."""
        # Banking-specific threats get higher priority
        banking_relevance = any(keyword in content for keyword in self.banking_keywords)
        
        # Critical keywords
        critical_keywords = ["critical", "emergency", "immediate", "active", "ongoing"]
        is_critical = any(keyword in content for keyword in critical_keywords)
        
        if is_critical and banking_relevance:
            return ThreatLevel.CRITICAL
        elif is_critical:
            return ThreatLevel.HIGH
        elif banking_relevance:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW
    
    def _extract_indicators(self, content: str) -> List[str]:
        """Extract threat indicators from content."""
        indicators = []
        
        # IP addresses
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        indicators.extend(re.findall(ip_pattern, content))
        
        # Domains
        domain_pattern = r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
        indicators.extend(re.findall(domain_pattern, content))
        
        # Hashes (MD5, SHA1, SHA256)
        hash_patterns = [
            r'\b[a-fA-F0-9]{32}\b',  # MD5
            r'\b[a-fA-F0-9]{40}\b',  # SHA1
            r'\b[a-fA-F0-9]{64}\b',  # SHA256
        ]
        for pattern in hash_patterns:
            indicators.extend(re.findall(pattern, content))
        
        return list(set(indicators))  # Remove duplicates
    
    def _classify_ioc(self, indicator: str) -> str:
        """Classify the type of indicator of compromise."""
        if re.match(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', indicator):
            return "IP"
        elif re.match(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b', indicator):
            return "Domain"
        elif re.match(r'\b[a-fA-F0-9]{32,64}\b', indicator):
            return "Hash"
        else:
            return "Unknown"
    
    def _calculate_confidence(self, content: str, threat_type: ThreatType) -> float:
        """Calculate confidence score for threat detection."""
        confidence = 0.5  # Base confidence
        
        # Multiple threat keywords increase confidence
        threat_keywords = sum(1 for pattern in self.threat_patterns[threat_type] 
                            if re.search(pattern, content, re.IGNORECASE))
        confidence += min(threat_keywords * 0.2, 0.3)
        
        # Banking relevance increases confidence
        if any(keyword in content for keyword in self.banking_keywords):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def generate_security_recommendations(self, threats: List[ThreatIndicator]) -> List[SecurityRecommendation]:
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
            
            recommendation = self._create_recommendation(threat_type, type_threats, max_level)
            recommendations.append(recommendation)
        
        return recommendations
    
    def _create_recommendation(self, threat_type: ThreatType, threats: List[ThreatIndicator], 
                             threat_level: ThreatLevel) -> SecurityRecommendation:
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
                    "Conduct security awareness training"
                ],
                "affected_systems": ["Endpoints", "Servers", "Network"],
                "estimated_effort": "4-6 hours",
                "compliance_impact": ["BSA/AML", "GLBA", "SOX"]
            },
            ThreatType.PHISHING: {
                "title": "Phishing Campaign Alert - Employee Training Required",
                "description": f"Identified {len(threats)} phishing indicators targeting financial institutions.",
                "action_items": [
                    "Send phishing awareness alerts to all employees",
                    "Review email security settings",
                    "Implement multi-factor authentication",
                    "Conduct phishing simulation exercises",
                    "Update email filtering rules"
                ],
                "affected_systems": ["Email Systems", "User Accounts", "Training"],
                "estimated_effort": "2-4 hours",
                "compliance_impact": ["BSA/AML", "GLBA", "FFIEC"]
            },
            ThreatType.RANSOMWARE: {
                "title": "Ransomware Threat - Critical Backup Review Required",
                "description": f"Detected {len(threats)} ransomware indicators. Verify backup integrity immediately.",
                "action_items": [
                    "Verify all backup systems are operational",
                    "Test disaster recovery procedures",
                    "Review network segmentation",
                    "Implement ransomware protection tools",
                    "Update incident response plan"
                ],
                "affected_systems": ["Backup Systems", "Network", "Endpoints"],
                "estimated_effort": "6-8 hours",
                "compliance_impact": ["BSA/AML", "GLBA", "SOX", "FFIEC"]
            },
            ThreatType.VULNERABILITY: {
                "title": "Critical Vulnerability Alert - Patch Management Required",
                "description": f"Identified {len(threats)} critical vulnerabilities requiring immediate patching.",
                "action_items": [
                    "Prioritize critical patches for immediate deployment",
                    "Review vulnerability management procedures",
                    "Conduct security assessments",
                    "Update patch management policies",
                    "Implement automated patch deployment"
                ],
                "affected_systems": ["All Systems", "Network Infrastructure"],
                "estimated_effort": "8-12 hours",
                "compliance_impact": ["GLBA", "SOX", "FFIEC"]
            }
        }
        
        config = recommendations_map.get(threat_type, {
            "title": f"{threat_type.value.title()} Threat Detected",
            "description": f"Detected {len(threats)} {threat_type.value} indicators.",
            "action_items": ["Review security controls", "Update incident response plan"],
            "affected_systems": ["All Systems"],
            "estimated_effort": "2-4 hours",
            "compliance_impact": ["General Compliance"]
        })
        
        return SecurityRecommendation(
            title=config["title"],
            description=config["description"],
            priority=threat_level,
            action_items=config["action_items"],
            affected_systems=config["affected_systems"],
            estimated_effort=config["estimated_effort"],
            compliance_impact=config["compliance_impact"]
        )
