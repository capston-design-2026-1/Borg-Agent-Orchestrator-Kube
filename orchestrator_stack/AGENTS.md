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
- Use near per-file commits for orchestrator module changes (simulator, predictor, referee, optimizer, etc. committed separately when practical)

## Open-Source Integration Policy

- Use upstream AIOpsLab integration through adapter classes in `layer2`
- Use RLlib for multi-agent PPO through `layer4/rllib_env.py`
- Use Optuna for meta-optimization through `layer5/optuna_tuner.py`
- Keep version-sensitive notes in `README.md` and update when upstream major features change
