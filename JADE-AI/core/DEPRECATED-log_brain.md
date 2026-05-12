# ⚠️ DEPRECATED: LogBrain Moved to Platform

**Date:** 2026-02-12
**Status:** ⛔ DO NOT USE - Moved to GP-INFRA/platform/

---

## What Happened?

`log_brain.py` contained **platform functionality** (event normalization, routing) disguised as "brain" code.

During Phase 1.5 architectural cleanup, we moved it to the correct location:

```
❌ OLD: JADE-AI/core/log_brain.py (wrong - brain shouldn't route events)
✅ NEW: GP-INFRA/platform/ (correct - platform owns routing)
```

---

## Migration Guide

### Old Import (DEPRECATED):
```python
from JADE-AI.core.log_brain import LogBrain, NormalizedEvent, SourceType

brain = LogBrain()
events = brain.ingest(trivy_output, source_type=SourceType.TRIVY)
agent = brain.route_events(events)
```

### New Import (CORRECT):
```python
from GP-INFRA.platform.events import Event, EventSeverity, EventCategory, SourceType
from GP-INFRA.platform.services import get_event_router
from GP-INFRA.platform.normalizers import get_normalizer

# Normalize scanner output
normalizer = get_normalizer(SourceType.TRIVY)
events = normalizer.normalize(trivy_output)

# Route to agent
router = get_event_router()
for event in events:
    agent = router.route(event)  # Returns: "jsa-devsec" | "jsa-infrasec" | "jsa-secops"
```

---

## What Moved Where?

| Component | Old Location | New Location |
|-----------|--------------|--------------|
| **Event schema** | `log_brain.NormalizedEvent` | `GP-INFRA/platform/events/Event` |
| **Event enums** | `log_brain.EventSeverity`, `EventCategory`, `SourceType` | `GP-INFRA/platform/events/` |
| **Routing logic** | `LogBrain.route_events()` | `GP-INFRA/platform/services/EventRouter` |
| **Normalizers** | `LogBrain.normalizers` | `GP-INFRA/platform/normalizers/` |
| **TrivyNormalizer** | `log_brain.TrivyNormalizer` | `GP-INFRA/platform/normalizers/trivy.py` |
| **CheckovNormalizer** | `log_brain.CheckovNormalizer` | `GP-INFRA/platform/normalizers/checkov.py` |
| **KubernetesPodLogNormalizer** | `log_brain.KubernetesPodLogNormalizer` | `GP-INFRA/platform/normalizers/kubernetes.py` |
| **GitHubActionsNormalizer** | `log_brain.GitHubActionsNormalizer` | `GP-INFRA/platform/normalizers/github_actions.py` |
| **SemgrepNormalizer** | `log_brain.SemgrepNormalizer` | `GP-INFRA/platform/normalizers/semgrep.py` |
| **BanditNormalizer** | `log_brain.BanditNormalizer` | `GP-INFRA/platform/normalizers/bandit.py` |
| **GitleaksNormalizer** | `log_brain.GitleaksNormalizer` | `GP-INFRA/platform/normalizers/gitleaks.py` |
| **GrypeNormalizer** | `log_brain.GrypeNormalizer` | `GP-INFRA/platform/normalizers/grype.py` |
| **AWSGuardDutyNormalizer** | `log_brain.AWSGuardDutyNormalizer` | `GP-INFRA/platform/normalizers/aws_guardduty.py` |
| **AWSCloudWatchNormalizer** | `log_brain.AWSCloudWatchNormalizer` | `GP-INFRA/platform/normalizers/aws_cloudwatch.py` |
| **JSAAgentNormalizer** | `log_brain.JSAAgentNormalizer` | `GP-INFRA/platform/normalizers/jsa_agent.py` |

---

## Why Did We Move It?

**LogBrain was doing PLATFORM work, not BRAIN work:**

- ✅ **Platform concerns** (nervous system):
  - Event normalization from multiple sources
  - Event routing to agents
  - Event correlation and deduplication
  - **→ Moved to GP-INFRA/platform/**

- ✅ **Brain concerns** (intelligence):
  - LLM inference (stays in JADE-AI)
  - RAG retrieval (stays in JADE-AI)
  - Complex analysis (stays in JADE-AI)
  - **→ Stays in JADE-AI/**

---

## Timeline

- **Phase 1.5** (Complete): Event schema + routing migrated ✅
- **Phase 1.6** (Complete): Normalizers migrated ✅
- **Phase 2** (Next): Update all agent imports to new location
- **Phase 3** (Future): Keep LogBrain for intelligence features only (correlation, LLM analysis)

---

## Questions?

See architectural docs:
- `docs/architecture/platform-jade-separation.md`
- `docs/jade-coupling-audit.md`

**Bottom line:** If you're normalizing events or routing to agents, use GP-INFRA/platform, not JADE-AI.
