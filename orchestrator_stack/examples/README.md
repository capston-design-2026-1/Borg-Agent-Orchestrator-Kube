# Example Assets

- `sample_metrics.json`: Layer 1 input example (Prometheus/JSON-like flat rows; `.csv` files with matching columns are also accepted)
- `sample_trace.json`: Layer 1 output / Layer 2 input example trace rows
- `sample_telemetry_trace.json`: small trace with `sla_violations`, `completed_tasks`, and `energy_watts` for telemetry reward audits
- `generate_synthetic_assets.py`: creates synthetic `.npz` datasets and a larger metrics sample
- `models/`: output directory for trained risk/demand models

## Layer 1 Data Contracts

`sample_metrics.json` and CSV metric files accepted row shapes:

1. Flat Prometheus-like rows:
`timestamp`, `node_id`, and at least one metric in `cpu_util|mem_util|disk_util|net_util`
2. Grouped rows:
`timestamp`, `nodes` (list), `tasks` (list)

`sample_trace.json` row contract (validated by `load_trace_rows`):

- Required top-level keys per row: `timestamp`, `nodes`, `tasks`
- Required node keys: `node_id`, `cpu_util`, `mem_util`
- Required task keys: `task_id`, `node_id`
- Optional but validated when present: `queue_length` (non-negative int-like), `energy_price` (numeric), `task_death` (bool-like)
- Optional telemetry reward fields validated when present: `sla_violations` (non-negative int-like), `completed_tasks` (non-negative int-like), `energy_watts` (non-negative numeric)
- Optional task fields validated when present: `urgency` (numeric), `queue_priority` (non-negative int-like), `alive` (bool-like)
