# AI System Registration Form
## AI RMF GOVERN-1.1: Know Your AI System

**System Name**: JADE-v3
**Organization**: LinkOps Industries
**Registration Date**: 2026-04-26
**AI System Owner**: Chief Security Officer

### System Identification
- **Purpose**: AppSec Executor
- **Description**: Code+Cluster security engineer fixing SAST findings and misconfigurations
- **Type**: Generative AI
- **Model Base**: Llama 3.2-3B-Instruct
- **Training Data**: Real security findings from 5 clients

### Impact and Risk Tier
- **Impact Level**: MODERATE
- **Scope**: Single team internal use
- **Data Classification**: CONTROLLED UNCLASSIFIED
- **Risk Tier**: MEDIUM

### Planned Controls
- MAP-4.3: Documented decision log
- GOVERN-2.2: Documented decision log
- GOVERN-2.2: Human-in-the-loop gate

### Key Questions Answered
1. **Who authorized this AI system?** Security governance board (minutes attached)
2. **What performance targets?** ≥70% on NIST control mapping eval benchmark
3. **What's the fallback if AI fails?** Manual human review (no autonomous fixes above C-rank)
4. **What audit trail?** MLflow tracking + HITL approval logs in git
