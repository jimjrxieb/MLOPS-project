# BERU Knowledge Base

This is everything the BERU agent reads at runtime — bundled here so the model
ships self-contained. Clone the repo, run the agent, it has what it needs. No
external directories to mount, no submodules.

```
knowledge/
├── nist-800-53/
│   ├── playbooks/                 BERU audit playbooks: 00-beru-start-here + 6 family audits
│   │                              + 02-produce-poam + 03-produce-ssp-narrative + 04-ciso-briefing
│   ├── controls/                  42 NIST 800-53 Rev 5 control files (requirements, evidence
│   │                              checklist, owner questions, validating tools, failure shapes)
│   ├── templates/                 beru-finding.md, poam-item.md
│   ├── ssp-examples/              bad / good / great SSP narratives per family — the grading rubric
│   ├── poam-examples/             reference POA&M items
│   ├── risk-assessment-examples/  reference risk assessments
│   ├── 3POA/                      audit framework, MITRE ATT&CK map, tool-justification matrix,
│   │                              evidence-requests per lens
│   ├── control-owner-matrix.md    who owns each control (POA&M routing)
│   └── nist80053toc.md            control-family table of contents
└── frameworks/
    ├── nist-ai-600-1/             AI RMF GOVERN / MAP / MEASURE / MANAGE subcategories
    ├── crosswalk/                 800-53 ↔ AI RMF bidirectional mapping (the "tags" the
    │                              LangGraph control-context node uses for dual citation)
    └── mitre-atlas/               MITRE ATLAS technique IDs (referenced when an AI system
                                   is the target of an attack)
```

## Provenance

This is a **snapshot**. The canonical sources are:
- `nist-800-53/`  ←  `GP-CONSULTING/NIST-800-53/` (the GP-Copilot repo's playbook-as-brain corpus)
- `frameworks/`   ←  `GP-MODEL-OPS/CAPSTONE-PROJECT/frameworks/`

If the canonical sources change, re-sync:
```bash
GP_CONS=../../../GP-CONSULTING/NIST-800-53
cp -r $GP_CONS/{playbooks,controls,templates,ssp-examples,3POA,poam-examples,risk-assessment-examples} knowledge/nist-800-53/
cp    $GP_CONS/{control-owner-matrix.md,nist80053toc.md} knowledge/nist-800-53/
cp -r ../CAPSTONE-PROJECT/frameworks/{nist-ai-600-1,crosswalk,mitre-atlas} knowledge/frameworks/
```

## How the agent finds this

`agent/playbook_loader.py` defaults to `BERU-AI/knowledge/`. Override with the
`BERU_NIST_DIR` and `BERU_CROSSWALK_PATH` env vars to point at the canonical
sources instead (useful in a live GP-Copilot checkout where you want updates to
propagate without re-syncing).
