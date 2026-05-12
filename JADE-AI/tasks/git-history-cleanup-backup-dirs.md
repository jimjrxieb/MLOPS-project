# JADE Task: Remove Backup Directories from Git History

**Task Rank**: B-rank (Git internals, history rewriting, risk assessment)
**Assigned To**: JADE v0.3+ (via claude-code or autonomous execution)
**Priority**: Medium (non-critical, training opportunity)
**Risk Level**: Medium (rewrites git history, breaks existing clones - APPROVED for non-production repos)

---

## Problem Statement

Gitleaks scanner is finding 83 false positive "secrets" in historical git commits that reference now-deleted backup directories:
- `backup/eslint-fixes-20251030_132304/**`
- `backup/command-injection-*/**`
- `backup/dependency-vulns-*/**`
- `backup/weak-crypto-*/**`

These backup dirs were created by JSA's early fix attempts and committed to git history. Even though they're deleted from the filesystem, Gitleaks' history scanning finds them in old commits.

**Current Workaround**: D-rank path resolver skips all 83 findings (100% success rate)
**Desired State**: Remove backup directories from git history entirely

---

## Task Objectives

1. **Identify affected repos**: Find all repos with backup directories in git history
2. **Choose cleanup method**: BFG Repo Cleaner (fast) vs git filter-branch (built-in)
3. **Execute cleanup**: Remove ALL references to backup/** from git history
4. **Verify results**: Confirm Gitleaks no longer finds backup path secrets
5. **Document process**: Create training data for future git history cleanup tasks

---

## Pre-Execution Checklist

- [ ] Confirm repo is non-production (APPROVED: ai-powered-project is test repo)
- [ ] Verify no team members have active clones (single-user project - SAFE)
- [ ] Create backup of entire repo before starting
- [ ] Document current commit count and history size

---

## Method 1: BFG Repo Cleaner (RECOMMENDED)

**Why BFG**: 10-720x faster than git filter-branch, simpler syntax

### Installation
```bash
# Check if BFG is available
which bfg || echo "BFG not installed"

# Install BFG (if needed)
cd /tmp
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar
sudo mv bfg-1.14.0.jar /usr/local/bin/bfg.jar
echo 'alias bfg="java -jar /usr/local/bin/bfg.jar"' >> ~/.bashrc
source ~/.bashrc
```

### Execution
```bash
# Navigate to repo
cd /home/jimmie/linkops-industries/GP-copilot/GP-PROJECTS/01-instance/slots/ai-powered-project

# Create full backup
cd ..
tar -czf ai-powered-project-backup-$(date +%Y%m%d_%H%M%S).tar.gz ai-powered-project/
cd ai-powered-project

# Clone repo (BFG requires working with a mirror)
cd /tmp
git clone --mirror /home/jimmie/linkops-industries/GP-copilot/GP-PROJECTS/01-instance/slots/ai-powered-project/.git ai-powered-project-mirror.git
cd ai-powered-project-mirror.git

# Remove ALL references to backup/** directories from history
bfg --delete-folders backup

# Clean up refs and run garbage collection
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Push cleaned history back to original repo
cd /home/jimmie/linkops-industries/GP-copilot/GP-PROJECTS/01-instance/slots/ai-powered-project
git pull /tmp/ai-powered-project-mirror.git

# Force push to update remote (if any)
# git push --force origin main
```

---

## Method 2: Git Filter-Branch (BUILT-IN)

**Why filter-branch**: No external dependencies, works everywhere

### Execution
```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-PROJECTS/01-instance/slots/ai-powered-project

# Create full backup first
cd ..
tar -czf ai-powered-project-backup-$(date +%Y%m%d_%H%M%S).tar.gz ai-powered-project/
cd ai-powered-project

# Remove backup/** directories from ALL commits
git filter-branch --force --index-filter \
  'git rm -r --cached --ignore-unmatch backup/' \
  --prune-empty --tag-name-filter cat -- --all

# Clean up refs
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Verify backup dirs are gone
git log --all --pretty=format: --name-only --diff-filter=A | sort -u | grep backup
# Should return nothing

# Force push (if remote exists)
# git push --force --all
# git push --force --tags
```

---

## Verification Steps

1. **Check git history is clean**:
   ```bash
   git log --all --oneline | head -20
   # Should show commits, but no backup references

   git log --all --pretty=format: --name-only | grep backup
   # Should return empty
   ```

2. **Run Gitleaks scan manually**:
   ```bash
   cd /home/jimmie/linkops-industries/GP-copilot/GP-CONSULTING/1-Security-Assessment
   python3 -c "
   from npcs import GitleaksNPC
   npc = GitleaksNPC()
   result = npc.run('/home/jimmie/linkops-industries/GP-copilot/GP-PROJECTS/01-instance/slots/ai-powered-project')
   print(f'Findings: {len(result[\"findings\"])}')
   print(f'Expected: 0 (or very few real findings)')
   "
   ```

3. **Wait for JSA-01 next scan cycle**:
   ```bash
   # Monitor for new gitleaks scan log
   watch -n 10 'ls -lt /home/jimmie/linkops-industries/GP-copilot/GP-MLModels/jadeSecureAgent/logs/01-instance/scans/ | grep gitleaks | head -1'

   # Check findings count in latest scan
   grep "Findings:" /home/jimmie/linkops-industries/GP-copilot/GP-MLModels/jadeSecureAgent/logs/01-instance/scans/gitleaks_slot01_*.log | tail -1
   ```

---

## Expected Results

**Before Cleanup**:
- Gitleaks findings: 83 (all backup paths)
- Git history size: ~X MB
- Commit count: Y commits

**After Cleanup**:
- Gitleaks findings: 0-2 (only real secrets, if any)
- Git history size: Reduced by ~X MB
- Commit count: Y commits (same, but content changed)
- JSA-01 scan time: Reduced from 32s to ~5s (no backup paths to scan)

---

## Rollback Plan

If something goes wrong:

```bash
cd /home/jimmie/linkops-industries/GP-copilot/GP-PROJECTS/01-instance/slots
rm -rf ai-powered-project
tar -xzf ai-powered-project-backup-YYYYMMDD_HHMMSS.tar.gz
```

---

## Training Data Generation

After successful cleanup, JADE should generate training examples:

1. **Problem identification**: Recognizing git history pollution
2. **Risk assessment**: When is history rewriting safe vs dangerous?
3. **Tool selection**: BFG vs filter-branch trade-offs
4. **Execution strategy**: Backup → Clean → Verify → Document
5. **Verification**: Multiple methods to confirm success

Save to: `/home/jimmie/linkops-industries/GP-copilot/GP-DATA/HyperbolicRagChamber/01-unprocessed/operational-training-data/YYYYMMDD-git-history-cleanup-backup-dirs.md`

---

## JADE Execution Command

```bash
# From claude-code or JADE autonomous mode:
cd /home/jimmie/linkops-industries/GP-copilot/JADE-AI/tasks
# Read this file and execute Method 1 (BFG) or Method 2 (filter-branch)
# Generate training data upon completion
```

---

## Notes for JADE

- This is a **B-rank task** - requires understanding of:
  - Git internals (commits, trees, blobs, refs)
  - History rewriting implications
  - Backup/recovery strategies
  - Verification methods

- **Learning objectives**:
  - When is it safe to rewrite git history?
  - How to verify destructive operations?
  - Trade-offs between different git cleanup tools

- **Future applications**:
  - Cleaning accidentally committed secrets
  - Removing large files from history
  - Squashing old commits
  - Repository maintenance automation
