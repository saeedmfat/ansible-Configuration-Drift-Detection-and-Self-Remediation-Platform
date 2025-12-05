# 🔍 Configuration Drift Detection & Self-Remediation Platform

[![Project Status](https://img.shields.io/badge/status-production-green)](https://github.com/saeedmfat/ansible-Configuration-Drift-Detection-and-Self-Remediation-Platform)
[![Ansible](https://img.shields.io/badge/ansible-2.9+-blue)](https://www.ansible.com)
[![Python](https://img.shields.io/badge/python-3.8+-yellow)](https://python.org)
[![Vagrant](https://img.shields.io/badge/vagrant-2.2+-orange)](https://vagrantup.com)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://www.linkedin.com/in/saeed-marefat-b97992349)

## 🎯 Project Goal

**Configuration drift** is the silent killer of production systems - unauthorized changes that accumulate over time, leading to inconsistencies, security vulnerabilities, and system failures. This project solves this critical problem by building a complete **enterprise-grade automation platform** that:

1. **Continuously monitors** infrastructure for unauthorized changes
2. **Automatically detects** configuration drift using checksum validation
3. **Safely self-remediates** using canary deployment patterns
4. **Creates immutable audit trails** of all changes
5. **Provides real-time reporting** via REST API and dashboards

The system emulates real production infrastructure while staying within **16GB RAM home lab constraints**, making it accessible for learning and practical implementation.

## 🏗️ Architecture Overview

```mermaid
graph TB
    subgraph "HOST MACHINE (16GB RAM)"
        subgraph "CONTROL NODE (2GB RAM)"
            C1[Ansible Controller]
            C2[Git Server<br/>config-drift.git]
            C3[Drift Simulator<br/>Python/Faker]
            C4[Detection Engine<br/>Checksum Validation]
            C5[Flask API Server<br/>Port 8080]
            C6[Notification System]
            C7[Remediation Engine<br/>Canary Logic]
            
            C1 --> C2
            C3 --> C4
            C4 --> C5
            C4 --> C7
            C5 --> C6
            C7 --> C1
            C7 --> C6
        end
        
        subgraph "NETWORK 192.168.60.0/24"
            subgraph "TARGET 1 (2GB RAM)"
                T1A[Ubuntu 20.04]
                T1B[Nginx Web Server]
                T1C[Ansible-Pull Client]
                T1D[/var/www/config-drift-website/]
                
                T1A --> T1B
                T1B --> T1D
                T1A --> T1C
            end
            
            subgraph "TARGET 2 (2GB RAM)"
                T2A[Ubuntu 20.04]
                T2B[Nginx Web Server]
                T2C[Ansible-Pull Client]
                T2D[/var/www/ubuntu-website/]
                
                T2A --> T2B
                T2B --> T2D
                T2A --> T2C
            end
            
            subgraph "TARGET 3 (2GB RAM)"
                T3A[Rocky Linux 8]
                T3B[Apache Web Server]
                T3C[Ansible-Pull Client]
                T3D[/var/www/rocky-website/]
                
                T3A --> T3B
                T3B --> T3D
                T3A --> T3C
            end
        end
    end
    
    %% Data Flow
    C1 -- "Ansible Push<br/>SSH/Playbooks" --> T1A
    C1 -- "Ansible Push<br/>SSH/Playbooks" --> T2A
    C1 -- "Ansible Push<br/>SSH/Playbooks" --> T3A
    
    C3 -- "Simulated Drifts" --> T1D
    C3 -- "Simulated Drifts" --> T2D
    C3 -- "Simulated Drifts" --> T3D
    
    C4 -- "Checksum Validation" --> T1D
    C4 -- "Checksum Validation" --> T2D
    C4 -- "Checksum Validation" --> T3D
    C4 -- "Service Status Check" --> T1B
    C4 -- "Service Status Check" --> T2B
    C4 -- "Service Status Check" --> T3B
    
    C5 -- "API Queries" --> Human[Human Operator]
    C6 -- "Alerts/Notifications" --> Human
    
    C2 -- "Git Pull" --> T1C
    C2 -- "Git Pull" --> T2C
    C2 -- "Git Pull" --> T3C
    
    C7 -- "Canary Remediation<br/>(target1 first)" --> T1A
    C7 -- "Full Remediation" --> T2A
    C7 -- "Full Remediation" --> T3A
    
    %% Sub-processes
    subgraph "DETECTION WORKFLOW"
        DW1[File Checksum<br/>Calculation]
        DW2[State Comparison<br/>vs Desired State]
        DW3[Drift Classification<br/>Critical/High/Medium/Low]
        DW4[Report Generation<br/>JSON/HTML/Markdown]
        
        DW1 --> DW2
        DW2 --> DW3
        DW3 --> DW4
    end
    
    subgraph "REMEDIATION WORKFLOW"
        RW1[Canary Selection<br/>25% of nodes]
        RW2[Pre-remediation<br/>Validation]
        RW3[Backup Creation]
        RW4[Apply Fixes]
        RW5[Post-remediation<br/>Validation]
        RW6[Success?] -->|Yes| RW7[Full Rollout]
        RW6 -->|No| RW8[Automatic Rollback]
        
        RW1 --> RW2
        RW2 --> RW3
        RW3 --> RW4
        RW4 --> RW5
        RW5 --> RW6
    end
    
    subgraph "AUDIT TRAIL"
        AT1[Git Commit<br/>Detection Events]
        AT2[Git Commit<br/>Remediation Actions]
        AT3[Immutable Log<br/>All Changes]
        
        AT1 --> AT3
        AT2 --> AT3
    end
    
    %% Connections to sub-processes
    C4 --> DW1
    DW4 --> C5
    DW4 --> AT1
    
    C7 --> RW1
    RW7 --> AT2
    RW8 --> AT2
    
    %% Scheduling
    subgraph "SCHEDULING (Systemd Timers)"
        S1[Drift Simulation<br/>Every 2 hours]
        S2[Drift Detection<br/>Every 15 minutes]
        S3[Ansible-Pull<br/>Every 30 minutes]
        S4[Daily Reports<br/>11:30 PM]
        
        S1 --> C3
        S2 --> C4
        S3 --> T1C
        S3 --> T2C
        S3 --> T3C
        S4 --> C5
    end
    
    %% Legend
    subgraph "LEGEND"
        L1[💻 Process/Service]
        L2[📁 Directory/Data]
        L3[🔗 Communication]
        L4[🔄 Workflow]
        L5[⏰ Scheduling]
    end
    
    %% Styling
    classDef control fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef target fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    classDef workflow fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef audit fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef schedule fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef network fill:#f5f5f5,stroke:#616161,stroke-width:1px,dashed
    
    class C1,C2,C3,C4,C5,C6,C7 control
    class T1A,T1B,T1C,T2A,T2B,T2C,T3A,T3B,T3C target
    class T1D,T2D,T3D target
    class DW1,DW2,DW3,DW4,RW1,RW2,RW3,RW4,RW5,RW6,RW7,RW8 workflow
    class AT1,AT2,AT3 audit
    class S1,S2,S3,S4 schedule
    class NETWORK network
```


## 📁 Project Structure

### Core Directories

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| **`inventories/`** | Ansible inventory management | `production/hosts.ini` - Production node definitions |
| **`playbooks/`** | Automation workflows | `webserver-deploy.yml` - Main deployment<br>`master-remediate.yml` - Canary remediation |
| **`roles/`** | Reusable Ansible components | `base/` - System fundamentals<br>`webserver/` - Web server configuration |
| **`detection-system/`** | Drift detection engine | `drift_detector.py` - Core detection logic<br>`report_api.py` - Flask REST API |
| **`drift-simulator/`** | Drift injection for testing | `drift_simulator.py` - Random drift generator |
| **`remediation-system/`** | Auto-remediation logic | `remediation_engine.py` - Safe remediation with rollback |
| **`notification-system/`** | Alerting system | `notify.sh` - Multi-channel notifications |
| **`scripts/`** | Utility scripts | `monitoring-dashboard.sh` - Live monitoring<br>`run-end-to-end-workflow.sh` - Complete demo |
| **`reports/`** | Generated reports | JSON/HTML/Markdown reports with timestamps |
| **`systemd-scheduling/`** | Automation scheduling | Timer/service files for all components |

### Key Configuration Files

| File | Description |
|------|-------------|
| **`Vagrantfile`** | Defines 4 VMs (1 control + 3 targets) |
| **`ansible.cfg`** | Ansible configuration and defaults |
| **`README-FINAL.md`** | Complete project documentation |
| **`QUICK-REFERENCE.md`** | Command cheat sheet |
| **`FINAL-SUMMARY.md`** | Project completion summary |

## 🚀 Project Stages (7-Stage Journey)

### Stage 1: Home Lab Setup
- ✅ Created 4 VMs using Vagrant + VirtualBox
- ✅ Configured private networking (192.168.60.0/24)
- ✅ Set up SSH key authentication
- ✅ Installed Ansible on control node
- ✅ Initialized Git repository for configuration

### Stage 2: Project Skeleton & Inventory
- ✅ Created professional Ansible directory structure
- ✅ Built separate inventories for Ubuntu/Rocky nodes
- ✅ Implemented group variables and host-specific configs
- ✅ Created base role with fundamental system configuration
- ✅ Demonstrated idempotency with test playbooks

### Stage 3: Desired State Role Development
- ✅ Built comprehensive webserver role (Nginx/Apache)
- ✅ Created configuration templates with variables
- ✅ Implemented custom facts for drift detection
- ✅ Added checksum-based state validation
- ✅ Demonstrated zero-downtime configuration updates

### Stage 4: Drift Simulation System
- ✅ Created Python-based drift simulator
- ✅ Implemented weighted random drift scenarios
- ✅ Added safe mode for testing
- ✅ Set up systemd timers for automated simulation
- ✅ Built drift analysis and reporting tools

### Stage 5: Drift Detection & Reporting
- ✅ Developed checksum-based detection engine
- ✅ Created multi-format reporting (JSON/HTML/Markdown)
- ✅ Built Flask REST API for report serving
- ✅ Implemented Git-based audit trail system
- ✅ Added real-time notification integration

### Stage 6: Self-Remediation Logic
- ✅ Implemented canary deployment for safe remediation
- ✅ Created threshold-based safety logic
- ✅ Built automatic rollback mechanisms
- ✅ Added pre/post validation checks
- ✅ Developed specialized remediation playbooks

### Stage 7: Automation Scheduling
- ✅ Set up ansible-pull for distributed management
- ✅ Created comprehensive systemd timer scheduling
- ✅ Built monitoring dashboard with real-time status
- ✅ Implemented end-to-end workflow demonstration
- ✅ Added multi-channel notification system

## 🛠️ Quick Start

### Prerequisites
- 16GB RAM system
- VirtualBox 6.1+
- Vagrant 2.2+
- Git

### Installation
```bash
# Clone the repository
git clone https://github.com/saeedmfat/ansible-Configuration-Drift-Detection-and-Self-Remediation-Platform.git
cd ansible-Configuration-Drift-Detection-and-Self-Remediation-Platform

# Start the virtual environment
vagrant up

# Connect to control node
vagrant ssh control
cd ~/ansible-config-drift

# Deploy initial configuration
ansible-playbook -i inventories/production/hosts.ini playbooks/webserver-deploy.yml
```

### Monitoring Dashboard
```bash
./scripts/monitoring-dashboard.sh
```

### Run Complete Demo
```bash
./scripts/run-end-to-end-workflow.sh
```

## 📊 System Features

| Feature | Implementation | Benefit |
|---------|---------------|---------|
| **Continuous Monitoring** | 15-minute detection intervals | Proactive issue detection |
| **Canary Remediation** | Test fixes on 25% of nodes first | Safe production changes |
| **Immutable Audit Trail** | Git-based logging | Compliance and forensics |
| **Multi-format Reports** | JSON, HTML, Markdown | Human and machine readable |
| **REST API** | Flask-based API server | Integration ready |
| **Real-time Notifications** | Slack/Email/Terminal alerts | Immediate awareness |
| **Resource Efficient** | Fits in 16GB RAM | Accessible home lab |

## 🧪 Testing & Validation

### System Health Check
```bash
./scripts/validate-complete-system.sh
```

### End-to-End Test
```bash
./scripts/run-end-to-end-workflow.sh
```

### Manual Operations
```bash
# Check for drifts
cd detection-system && python3 scripts/drift_detector.py

# Remediate manually
ansible-playbook -i inventories/production/hosts.ini playbooks/master-remediate.yml

# View reports
curl http://localhost:8080/api/v1/reports/latest | jq .
```

## 📈 Performance Metrics

- **Detection Time**: ~30 seconds per node
- **Remediation Time**: 2-5 minutes (depending on drifts)
- **Memory Usage**: 8GB VMs + 4GB overhead = 12GB total
- **Storage**: ~5GB including logs and reports
- **Scalability**: Supports up to 50 nodes within constraints

## 🔒 Security Features

- Private network isolation (192.168.60.0/24)
- SSH key authentication only
- No external dependencies
- Local Git repositories
- API binds to localhost only
- Comprehensive audit logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/improvement`)
5. Create Pull Request


## 👨‍💻 Author

**Saeed Marefat**
- LinkedIn: [https://www.linkedin.com/in/saeed-marefat-b97992349](https://www.linkedin.com/in/saeed-marefat-b97992349)
- GitHub: [https://github.com/saeedmfat](https://github.com/saeedmfat)

## 🌟 Acknowledgments

- Inspired by real-world production configuration management challenges
- Built for DevOps engineers transitioning to infrastructure automation
- Special thanks to the Ansible and open-source communities

---

**⭐ If you find this project useful, please give it a star on GitHub!**

## 📞 Support

For questions, issues, or contributions:
1. Open a [GitHub Issue](https://github.com/saeedmfat/ansible-Configuration-Drift-Detection-and-Self-Remediation-Platform/issues)
2. Connect on [LinkedIn](https://www.linkedin.com/in/saeed-marefat-b97992349)

---

**🎯 Remember:** Configuration drift is inevitable. Automation is the solution. This platform provides that solution in a complete, production-ready package.

**🚀 Happy Automating!**
