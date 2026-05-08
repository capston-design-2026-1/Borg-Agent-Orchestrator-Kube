# Orchestrator Stack Agents Guide

## Scope

This directory is isolated from the baseline/advanced XGBoost tracks and owns the full 6-layer orchestrator implementation.

## Agent Roles

- Agent A (Risk Mitigator): migration-first policy to protect task survival
- Agent B (Efficiency Optimizer): energy and consolidation policy
- Agent C (Gatekeeper): admission control and queue protection
- Referee: deterministic conflict resolver with safety-first precedence

## Engineering Policy

- Keep Layer boundaries explicit (`layer1` to `layer6`)
- Route every cross-layer interaction through typed data models (`types.py`)
- Preserve backend portability: local trace twin and AIOpsLab adapter must remain API-compatible
- Preserve objective portability: heuristic runner and RLlib wrapper must share reward semantics
- Keep `orchestrator_stack/scripts/launch_orchestration.sh`, `docs/ORCHESTRATION_LAUNCH.md`, and `orchestrator_stack/dashboard/` aligned with architecture changes so the thesis demo path stays one command
- Keep `docs/en/DASHBOARD_GUIDE.md` and `docs/ko/DASHBOARD_GUIDE.md` aligned whenever dashboard UI, event/state schemas, agent action semantics, reward formulas, Optuna/Ray display, or Kubernetes exerciser behavior changes
- Use one tracked file per commit for orchestrator work. Treat simulator, predictor, referee, optimizer, dashboard, script, manifest, test, and documentation edits as separate commits even when they belong to one feature.
- Before committing, verify `git diff --cached --name-only` lists exactly one intended file unless a mechanically inseparable exception from the repository root `AGENTS.md` applies.
- Do not batch dashboard, script, Kubernetes manifest, test, and documentation files into one commit for convenience.

## Open-Source Integration Policy

- Use upstream AIOpsLab integration through adapter classes in `layer2`
- Use RLlib for multi-agent PPO through `layer4/rllib_env.py`
- Use Optuna for meta-optimization through `layer5/optuna_tuner.py`
- Keep version-sensitive notes in `README.md` and update when upstream major features change
