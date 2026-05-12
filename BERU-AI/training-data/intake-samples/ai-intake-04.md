# AI System Registration Form
## AI RMF GOVERN-1.1: Know Your AI System

**System Name**: BERU-v4
**Organization**: LinkOps Industries
**Registration Date**: 2026-02-09
**AI System Owner**: Chief Security Officer

### System Identification
- **Purpose**: GRC Analyst Agent
- **Description**: Compliance assessor reading scanner output, mapping to NIST controls
- **Type**: Discriminative AI
- **Model Base**: Llama 3.2-3B-Instruct
- **Training Data**: Synthetic scenario data from 0-data-lab

### Impact and Risk Tier
- **Impact Level**: HIGH
- **Scope**: Company-wide security operations
- **Data Classification**: INTERNAL USE ONLY
- **Risk Tier**: HIGH

### Planned Controls
- MAP-1.2: Continuous evaluation metrics
- MAP-4.2: Human-in-the-loop gate
- MANAGE-2.1: Continuous evaluation metrics

### Key Questions Answered
1. **Who authorized this AI system?** Security governance board (minutes attached)
2. **What performance targets?** ≥70% on NIST control mapping eval benchmark
3. **What's the fallback if AI fails?** Manual human review (no autonomous fixes above C-rank)
4. **What audit trail?** MLflow tracking + HITL approval logs in git
