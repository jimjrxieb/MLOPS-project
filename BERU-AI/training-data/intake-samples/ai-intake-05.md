# AI System Registration Form
## AI RMF GOVERN-1.1: Know Your AI System

**System Name**: BERU-v5
**Organization**: LinkOps Industries
**Registration Date**: 2026-04-25
**AI System Owner**: Chief Security Officer

### System Identification
- **Purpose**: GRC Analyst Agent
- **Description**: Compliance assessor reading scanner output, mapping to NIST controls
- **Type**: Generative AI
- **Model Base**: Llama 3.2-3B-Instruct
- **Training Data**: Open source NIST playbooks + documentation

### Impact and Risk Tier
- **Impact Level**: MODERATE
- **Scope**: Customer-facing audit reports
- **Data Classification**: CONTROLLED UNCLASSIFIED
- **Risk Tier**: MEDIUM

### Planned Controls
- MANAGE-1.2: Documented decision log
- MAP-3.3: Documented decision log
- MANAGE-1.1: Human-in-the-loop gate

### Key Questions Answered
1. **Who authorized this AI system?** Security governance board (minutes attached)
2. **What performance targets?** ≥70% on NIST control mapping eval benchmark
3. **What's the fallback if AI fails?** Manual human review (no autonomous fixes above C-rank)
4. **What audit trail?** MLflow tracking + HITL approval logs in git
