# Repository Instructions

These instructions apply to work performed in this repository.

## Workflow Defaults

- Continue to the next logical engineering step unless the user explicitly tells you to stop or redirect.
- Make code changes directly rather than stopping at analysis when the next implementation step is clear.
- Keep momentum through implementation, verification, commit, and push.
- Preserve working conventions across sessions by recording durable workflow, reporting, and handoff rules in repository files rather than keeping them only in transient context.

## Git Workflow

- Always commit after making meaningful changes in this repository.
- Always push committed changes to the remote branch for this repository.
- Do not ask the user for permission before committing or pushing.
- Commit every tracked file independently by default: one changed file means one commit, and ten changed files means ten separate commits.
- Stage exactly one tracked file path per commit unless a listed exception below applies.
- Do not use broad staging commands such as `git add .`, `git add -A`, or directory-wide `git add <dir>` for a commit. Stage explicit file paths only.
- Before every commit, verify the staged set with `git diff --cached --name-only`; if more than one file is staged, unstage and split the commit.
- After every commit, verify the commit shape with `git show --name-only --oneline --stat HEAD` and make sure the commit contains only the intended file.
- Only group multiple files in one commit when they are mechanically inseparable and the repository would be invalid or misleading if committed separately, such as a generated lockfile with its manifest, a package metadata file with its generated checksum, or an `__init__.py` required solely to expose the same new module. Mention the exception in the commit message or final handoff.
- Do not group files because they share a feature, were edited together, are both documentation, are both tests, or because many commits feel inconvenient.
- If one session touches multiple concerns, stage, commit, validate, and push each file independently in the order those files were validated.
- When working in a single file, still shard commits by function, feature slice, or behavior change where practical.
- Use clear commit messages that describe the specific unit of work.

## Continuity And Memory

- When a session establishes a new durable working convention, store it in `Agents.md`, `NEXT_STEPS.md`, `README.md`, or another appropriate tracked file before ending the work.
- Keep `NEXT_STEPS.md` current enough that a new Codex session can resume with the same operational assumptions and current priorities.
- Keep user-facing workflow changes in `README.md` when they affect how the repository should be used.
- Keep copy-paste-safe launch commands in `README.md` and `docs/ORCHESTRATION_LAUNCH.md` when launcher behavior changes; include a one-line command when multiline shell continuations could be mistyped.
- Use timestamp-prefixed report filenames in KST format `YYYYMMDDHHMM_*` for report artifacts stored in the repository.
- If the user types `milestone`, treat that as an instruction to record the current state for the next Codex context.
- On `milestone`, update the relevant tracked memory files for the work that was completed, especially `NEXT_STEPS.md`, `README.md`, `Agents.md`, and report files when applicable.
- On `milestone`, commit and push those updates using the repository's split-commit policy instead of bundling all persistence changes together.

## Data Layout

- Prefer keeping large Borg data outside the repository under `~/Documents`.
- Treat `~/Documents/borg_data` as the default raw data location.
- Treat `~/Documents/borg_processed` as the default processed data location.
- Treat `~/Documents/borg_xgboost_workspace` as the dedicated root for the advanced XGBoost track, with its own `raw`, `processed`, `models`, `reports`, `runtime`, and `config` subtrees.
- Do not mix advanced-model raw data or artifacts into `~/Documents/borg_data` or `~/Documents/borg_processed`; the first baseline task and the advanced task must stay isolated at the directory-root level.
- Do not commit generated datasets or large external data files into git.
- When a new parquet type or artifact directory is created under the external processed-data tree, add a schema or artifact explanation file in that same directory describing what the files mean and what the important columns represent.
- Do not rely only on repository docs for parquet meanings; keep a local README-style explanation beside the actual generated outputs.

## Cluster Defaults

- Default processing targets are clusters `b`, `c`, `d`, `e`, `f`, and `g`.
- Exclude clusters `a` and `h` by default unless the user explicitly asks to include them.

## Approval Behavior

- Do not ask the user for approval for routine repository workflow actions such as commits and pushes.
- If the runtime or sandbox requires an approval flow outside repository policy, comply with the runtime requirement, but do not ask for git workflow approval on your own initiative.

## Isolated Orchestrator Track

- Keep full 6-layer orchestrator implementation work under `orchestrator_stack/` so it does not mix with baseline or advanced XGBoost tracks.
- Use `orchestrator_stack/AGENTS.md` and `orchestrator_stack/NEXT_STEPS.md` as the first continuity references when resuming orchestrator-specific tasks.
- When the repository-wide orchestration architecture changes, keep the one-command launcher and visualization path synchronized in the same session: `orchestrator_stack/scripts/launch_orchestration.sh`, `docs/ORCHESTRATION_LAUNCH.md`, and `orchestrator_stack/dashboard/`.
- When dashboard UI, runtime state fields, event schemas, Agent A/B/C action semantics, rewards, Optuna/Ray display, or Kubernetes stimulus behavior changes, update both dashboard guides in the same session: `docs/en/DASHBOARD_GUIDE.md` and `docs/ko/DASHBOARD_GUIDE.md`.

## Isolated Autonomy Track

- Keep autonomous Codex supervisor work under `codex_autonomy/` so it does not mix with model-training tracks.
- Use `codex_autonomy/README.md`, `codex_autonomy/AGENTS.md`, and `codex_autonomy/NEXT_STEPS.md` when resuming autonomy-daemon work.
