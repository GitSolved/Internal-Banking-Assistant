# Document Categorization System

## Overview

The Internal Assistant platform uses a cybersecurity-focused document categorization system to organize and classify uploaded documents based on their content and purpose. This system helps users quickly identify and access relevant security information.

## Categorization Categories

### 🔒 Security & Compliance
Documents related to security assessments, audits, compliance reports, and regulatory requirements.

**Keywords:** security assessment, security audit, compliance audit, vulnerability assessment, penetration test, security scan, risk assessment, security review, compliance, regulatory, certification, iso, soc, pci, dss, gdpr, sox

**Examples:**
- Security Assessment Reports
- Compliance Audit Documents
- Vulnerability Assessment Reports
- Penetration Testing Results
- Risk Assessment Documents
- ISO 27001 Certification Documents
- SOC 2 Reports
- GDPR Compliance Assessments

### 📋 Policy & Governance
Documents containing security policies, procedures, standards, and governance frameworks.

**Keywords:** policy, procedure, guideline, manual, handbook, protocol, standard, regulation, code of conduct, governance, framework, baseline, control, requirement, specification

**Examples:**
- Information Security Policy
- Acceptable Use Policy
- Incident Response Procedures
- Security Standards and Guidelines
- Code of Conduct Documents
- Governance Frameworks
- Security Baselines
- Control Requirements

### 🕵️ Threat Intelligence
Documents containing threat intelligence, indicators of compromise (IOCs), malware analysis, and threat actor information.

**Keywords:** threat intelligence, ioc, malware, apt, campaign, cve, exploit, mitre, att&ck, ttp, indicator, signature, yara, stix, taxii, threat, attack, vulnerability, ransomware, phishing

**Examples:**
- Threat Intelligence Reports
- IOC Collections
- Malware Analysis Reports
- APT Campaign Analysis
- CVE Databases
- MITRE ATT&CK Mappings
- YARA Rules
- STIX/TAXII Feeds

### 🚨 Incident Response
Documents related to security incidents, breach analysis, forensics, and incident response procedures.

**Keywords:** incident response, forensics, investigation, breach, attack, incident, compromise, intrusion, data breach, containment, eradication

**Examples:**
- Incident Response Plans
- Forensic Analysis Reports
- Breach Investigation Documents
- Attack Analysis Reports
- Incident Post-Mortems
- Containment Procedures
- Eradication Strategies
- Lessons Learned Documents

### 🔧 Technical & Infrastructure
Technical documents, architecture diagrams, system configurations, and infrastructure documentation.

**Keywords:** technical, architecture, design, api, database, system, infrastructure, code, development, software, hardware, network, blueprint, diagram, topology, schema, protocol, interface

**Examples:**
- System Architecture Documents
- Network Topology Diagrams
- API Documentation
- Database Schemas
- Infrastructure Blueprints
- Configuration Guides
- Technical Specifications
- Deployment Procedures

### 📊 Research & Analysis
Research documents, trend analysis, benchmarks, statistics, and general security research.

**Keywords:** research, analysis, study, report, whitepaper, survey, trend, forecast, insight, data, statistics, metrics, benchmark, comparison, evaluation, assessment, findings, conclusion, recommendation, summary

**Examples:**
- Security Research Papers
- Trend Analysis Reports
- Benchmark Studies
- Statistical Reports
- Security Metrics
- Comparative Analysis
- Evaluation Reports
- Security Insights

## Implementation Details

### Categorization Logic

The categorization system uses keyword-based classification with the following priority order:

1. **Security & Compliance** - Highest priority for security-related documents
2. **Policy & Governance** - Policy and procedure documents
3. **Threat Intelligence** - Threat-specific documents
4. **Incident Response** - Incident-related documents
5. **Technical & Infrastructure** - Technical documentation
6. **Research & Analysis** - Default category for all other documents

### File Analysis Process

1. **File Name Analysis** - Primary categorization based on filename keywords
2. **Content Analysis** - Secondary analysis based on document content (when available)
3. **Metadata Analysis** - Additional categorization based on file metadata

### Categorization Accuracy

The system is designed to provide accurate categorization for cybersecurity documents while maintaining flexibility for various document types. Documents that don't clearly fit into specific categories are classified as "Research & Analysis" to ensure no documents are lost.

## Usage in the UI

### Document Library Display

Documents are organized into folders in the UI based on their categories:

```
📁 Document Library
├── 🔒 Security & Compliance (5)
├── 📋 Policy & Governance (3)
├── 🕵️ Threat Intelligence (8)
├── 🚨 Incident Response (2)
├── 🔧 Technical & Infrastructure (4)
└── 📊 Research & Analysis (12)
```

### Filtering and Search

Users can filter documents by category to quickly find relevant information:

- **Category Filters** - Filter by specific categories
- **Keyword Search** - Search within categories
- **Combined Filters** - Combine category and keyword filters

### Statistics and Reporting

The system provides category-based statistics:

- Document counts by category
- Category distribution charts
- Trend analysis by category
- Usage statistics

## Migration from Old Categories

### Previous Categories (Deprecated)
- Financial
- Policy
- Compliance
- Customer
- Other

### New Categories (Current)
- Security & Compliance
- Policy & Governance
- Threat Intelligence
- Incident Response
- Technical & Infrastructure
- Research & Analysis

### Migration Benefits

1. **Cybersecurity Focus** - Categories align with security intelligence needs
2. **Better Organization** - More specific and relevant categories
3. **Improved Search** - Better keyword matching for security documents
4. **Enhanced Analytics** - More meaningful category-based reporting

## Configuration

### Customizing Categories

Categories can be customized by modifying the keyword lists in:
- `internal_assistant/ui/utils/data_processors.py`
- `internal_assistant/ui/ui.py`

### Adding New Categories

To add a new category:

1. Add the category name to the `type_counts` dictionary
2. Define keywords for the category
3. Update the categorization logic
4. Add UI display elements
5. Update documentation

### Category Icons

Each category uses specific emoji icons for visual identification:

- 🔒 Security & Compliance
- 📋 Policy & Governance
- 🕵️ Threat Intelligence
- 🚨 Incident Response
- 🔧 Technical & Infrastructure
- 📊 Research & Analysis

## Best Practices

### Document Naming

For optimal categorization, use descriptive filenames that include relevant keywords:

**Good Examples:**
- `Security_Assessment_Report_2024.pdf`
- `Incident_Response_Procedure_v2.1.docx`
- `Threat_Intelligence_APT29_Analysis.pdf`

**Poor Examples:**
- `report.pdf`
- `document.docx`
- `file.txt`

### Category Selection

When uploading documents:

1. **Review Auto-Categorization** - Check if the system correctly categorized your document
2. **Use Descriptive Names** - Include relevant keywords in filenames
3. **Consider Content** - Think about the document's primary purpose
4. **Update if Needed** - Re-upload with better naming if categorization is incorrect

## Troubleshooting

### Common Issues

1. **Incorrect Categorization**
   - Solution: Rename file with more descriptive keywords
   - Alternative: Re-upload with better filename

2. **Documents in Wrong Category**
   - Check filename for relevant keywords
   - Consider document content and purpose
   - Update filename if necessary

3. **Missing Categories**
   - Ensure document has relevant keywords in filename
   - Check if document fits existing categories
   - Consider if new category is needed

### Support

For categorization issues or suggestions:
1. Review this documentation
2. Check the keyword lists
3. Contact the development team
4. Submit feature requests for new categories

---

**Note:** This categorization system is designed to evolve with the platform's needs. Regular reviews and updates ensure it remains relevant and useful for cybersecurity intelligence operations.
