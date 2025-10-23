# Internal Banking Assistant
AI RAG Platform for Banking: Cybersecurity, Compliance, and Risk Management

**Internal Banking Assistant** empowers financial institutions to automate risk, monitor security threats, and streamline compliance processes. Built for banking IT, compliance, and risk teams, this platform runs 100% locally for privacy and regulatory safety.

## Banking Features
• Real-time vulnerability and threat intelligence
• Automated regulatory updates (FDIC, NY DFS, SEC, FFIEC)
• Multi-team support for Risk, Compliance, Legal, and IT
• Fast regulatory research and workflow automation

## Use Case Examples
- Track new CVEs impacting bank infrastructure
- Generate compliance briefings from latest SEC/Federal/NY DFS notices

---

## 🚀 Quick Start
### System Requirements
- Python 3.11.9 (exact version required)
- 8GB+ RAM
- 10GB+ storage
- Ollama (for Foundation-Sec-8B model)

### Option 1: Docker (Recommended)
```bash
git clone https://github.com/SecureYourGear/internal-assistant.git
cd internal-assistant/config/deployment/docker
docker-compose up -d
```

### Option 2: Manual Installation
```bash
git clone https://github.com/SecureYourGear/internal-assistant.git
cd internal-assistant
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
ollama pull foundation-sec-8b
```

---

## 🏗️ Architecture

### Key Capabilities
| Feature | Description | Response Time |
|---------|-------------|---------------|
| **General LLM Mode** | Fast threat assessments and security queries | 6-12 seconds |
| **RAG Mode** | Document-based compliance research and analysis | 12-20 seconds |
| **Feed Monitoring** | Real-time security news and vulnerability tracking | Auto-refresh (60min) |
| **MITRE Analysis** | Threat technique identification and attack chain mapping | On-demand |

### Technology Stack
- **Foundation-Sec-8B Model:** Cybersecurity-trained AI (q4_k_m quantization, 5.06 GB)
- **14+ Security Feeds:** CISA KEV, US-CERT, SANS ISC, NIST NVD, The Hacker News, Dark Reading, and more
- **MITRE ATT&CK Integration:** Automated threat pattern detection and technique mapping
- **CVE Tracking:** Real-time vulnerability monitoring with severity filtering
- **Threat Intelligence:** Automated threat analysis, security recommendations, APT tracking
- **100% Private:** All processing happens locally—no data leaves your infrastructure

### Core Components
- [Foundation-Sec-8B](https://huggingface.co/Foundation-Sec/Foundation-Sec-8B) - Cybersecurity AI model
- [Gradio](https://gradio.app/) - Web interface
- [FastAPI](https://fastapi.tiangolo.com/) - API framework

---

## ⚖️ Attribution & License
**Internal Assistant** is built on the [PrivateGPT](https://github.com/zylon-ai/private-gpt) RAG framework and has been extensively specialized for cybersecurity intelligence workflows.

### What's Different from PrivateGPT
While sharing the foundational RAG infrastructure (~30-40% code overlap), Internal Assistant adds:
- **Foundation-Sec-8B** cybersecurity-trained AI model
- **14+ security RSS feeds** (CISA KEV, US-CERT, SANS ISC, etc.)
- **MITRE ATT&CK framework** integration with automated technique detection
- **CVE tracking and monitoring** with real-time vulnerability alerts
- **Threat intelligence analysis** with security recommendations
- **Custom security-focused UI** with threat dashboards
- **~48,000+ lines of custom code** for cybersecurity features

**Original Project:** [PrivateGPT by Zylon AI](https://github.com/zylon-ai/private-gpt)
**License:** Apache 2.0 (maintained from original)
**Copyright:** See [LICENSE](LICENSE) file

---

This project is based on [PrivateGPT](https://github.com/zylon-ai/private-gpt) and has been heavily customized for cybersecurity workflows.

## 🆘 Support
- **Issues:** [GitHub Issues](https://github.com/SecureYourGear/internal-assistant/issues)
- **Documentation:** [https://secureyourgear.github.io/internal-assistant/](https://secureyourgear.github.io/internal-assistant/)

---

## 📊 Project Stats
- **Version:** 0.6.2
- **Python:** 3.11.9 (required)
- **License:** Apache 2.0
- **Repository:** [SecureYourGear/internal-assistant](https://github.com/SecureYourGear/internal-assistant)
