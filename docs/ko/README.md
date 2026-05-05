# Borg-MAS-Optimizer

Borg에서 영감을 받은 다중 에이전트 스케줄링 및 클러스터 최적화 시스템을 위한 프로젝트 스캐폴드입니다.

## 이중 언어 문서

저장소 수준 동반 문서는 이제 다음 위치에 있습니다.

- `docs/en`
- `docs/ko`
- `reports/en`
- `reports/ko`

원본 Markdown 파일은 표준 작업 문서로 남아 있으며, 언어 디렉토리는 체계적인 영어/한국어 동반자 액세스를 제공합니다.

## 대시보드 설명서

대시보드의 모든 패널, 그래프, runtime event, Agent A/B/C 작업, 보상 규칙, Optuna trace, Ray/RLlib 상태, Kubernetes stimulus field에 대한 상세 설명은 다음 문서를 참고하세요.

- `docs/ko/DASHBOARD_GUIDE.md`

## 구조

```text
.
├── AGENTS.md
├── MAS_ARCHITECTURE.md
├── scripts/
│   ├── download_shards.sh
│   ├── data_flattener.py
│   ├── make_dataset.py
│   ├── make_forecaster_dataset.py
│   └── train_forecaster_baseline.py
├── src/
│   ├── agents/
│   └── environment/
├── .gitignore
└── README.md
```

참고: 이 파일 시스템에서는 `AGENTS.md`이 기존 추적된 [`Agents.md`](/Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator/Agents.md) 경로를 통해 저장됩니다. 파일 이름은 대소문자를 구분하지 않기 때문입니다.

## 데이터 레이아웃

원시 Borg 데이터는 기본적으로 저장소 외부에 있어야 합니다.

- 기본 원시 데이터 경로: `~/Documents/borg_data`
- 기본 처리 데이터 경로: `~/Documents/borg_processed`
- Advanced XGBoost workspace 루트: `~/Documents/borg_xgboost_workspace`

두 스크립트 모두 환경 변수로 override될 수 있습니다.

```bash
export BORG_RAW_DIR=~/Documents/borg_data
export BORG_PROCESSED_DIR=~/Documents/borg_processed
python scripts/data_flattener.py
```

고급 모델 트랙의 경우 완전히 별도의 workspace을 만들어 사용하세요.

```bash
./scripts/setup_advanced_runtime.sh
./scripts/setup_advanced_xgboost_workspace.sh
./scripts/run_advanced_download.sh
```

해당 작업공간은 두 번째 ML 작업을 첫 번째 기준 작업과 격리된 상태로 유지합니다.

- 원시 다운로드는 `~/Documents/borg_xgboost_workspace/raw`으로 이동합니다.
- 편평하고 파생된 parquet parquet는 `~/Documents/borg_xgboost_workspace/processed`으로 이동합니다.
- XGBoost 모델은 `~/Documents/borg_xgboost_workspace/models/xgboost`으로 이동합니다.
- 실험 보고서는 `~/Documents/borg_xgboost_workspace/reports`으로 보내주세요.
- 고급 소스 코드는 `src/advanced_xgboost/` 및 `scripts/build_advanced_xgboost_dataset.py` 및 `scripts/train_advanced_xgboost.py`과 같은 전용 입력 스크립트 아래에 있습니다.

기본적으로 프로젝트는 `b`부터 `g`까지 클러스터를 처리합니다.
`a` 및 `h` 클러스터는 flatten된 사용 스키마가 기본 데이터 세트 그룹과 다르기 때문에 제외됩니다.

원본 단일 샤드 샘플을 기본 외부 위치에 다운로드하려면 다음 안내를 따르세요.

```bash
./scripts/download_shards.sh
```

`100 GB`과 같은 제한된 대상 크기로 원시 시작 세트를 확장하려면 바이트 대상 모드를 사용하십시오.

```bash
BORG_DOWNLOAD_MODE=target_bytes \
BORG_TARGET_RAW_BYTES=100000000000 \
BORG_TARGET_TOLERANCE_BYTES=50000000000 \
./scripts/download_shards.sh
```

고급 트랙을 실행하는 경우 먼저 고급 env 파일을 소싱하여 이 다운로드가 기준 샘플 디렉터리 대신 `~/Documents/borg_xgboost_workspace/raw`에 도달하도록 하세요.

단일 명령 고급 다운로드를 원하면 다음을 실행하세요.

```bash
./scripts/run_advanced_download.sh
```

해당 래퍼는 필요한 경우 고급 workspace을 생성하고, 누락된 경우 `~/Documents/borg_xgboost_workspace/config/advanced_xgboost.env`을 생성하고 이를 로드한 다음 일관된 대상 기반 다운로드를 시작합니다.

현재 고급 설정의 경우 기본값은 이제 바이트 대상이 아닌 고정 일치 샤드 계획입니다.

- 클러스터: `b`~@@PLH0040@@@
- 머신 샤드: `000000000000`
- 이벤트 샤드: 클러스터당 첫 번째 `15`
- 사용 샤드: 클러스터당 첫 번째 `15`
- 기존 파일은 자동으로 건너뜁니다.

이는 귀하가 요청한 정적 `90 GB` 계획과 유사하게 작성되었습니다.

- `0.5 GB` 이벤트 + `0.5 GB` 샤드 인덱스당 사용량
- `15` 샤드 인덱스
- `6` 클러스터
- 기계 크기를 무시하고 총 `90 GB` 정도

분리된 Advanced feature 세트를 구축하고 XGBoost 오류 위험 모델을 교육하려면 다음을 실행하세요.

```bash
./scripts/run_advanced_xgboost_pipeline.sh
```

해당 파이프라인은 기본 예측 흐름과 의도적으로 분리되어 있습니다.

- 고급 작업공간에서 결합된 데이터세트를 읽습니다.
- `~/Documents/borg_xgboost_workspace/processed/feature_store` 아래에 Advanced feature parquet를 작성합니다.
- `~/Documents/borg_xgboost_workspace/models/xgboost` 아래에 XGBoost 모델 및 메트릭을 작성합니다.
- 동일한 높은 수준의 목표군을 유지합니다. 구성된 예측 horizon 내에서 실패/오류에 대한 위험 점수를 매깁니다.
- 누락된 기능이 있는 레이블 유효 행을 유지하고, 주요 기능에 대해 명시적인 `*_is_missing` 표시기를 추가하며, XGBoost가 조인된 전체 행을 삭제하는 대신 숫자 Null을 누락된 값으로 사용할 수 있도록 합니다.
- 이제 `5`, `15`, `30`, `45` 및 `60` 분에 대한 기본 레이블을 사용하여 동일한 조인된 데이터 세트 및 기능 parquet에서 여러 예측 horizon를 지원합니다.

고급 단계를 별도로 실행할 수도 있습니다.

```bash
./scripts/run_advanced_flatten.sh
./scripts/run_advanced_join.sh
./scripts/run_advanced_join_resumable.sh
./scripts/run_advanced_feature_build.sh
./scripts/run_advanced_feature_build_resumable.sh
./scripts/run_advanced_train.sh
./scripts/run_advanced_train_resumable.sh
```

고급 트랙에서 장기간 무인 주행을 하려면 재개 가능한 래퍼를 선호합니다.

- `run_advanced_join_resumable.sh`은 조인된 parquet가 이미 존재하는 클러스터를 건너뜁니다.
- `run_advanced_feature_build_resumable.sh` 기능 parquet이 이미 존재하는 클러스터를 건너뜁니다.
- `run_advanced_train_resumable.sh`은 모델 및 메트릭 아티팩트가 이미 존재하는 목표 horizon를 건너뜁니다.

고급 트레이너는 이제 제한된 결정론적 네거티브 샘플링을 사용하므로 각 학습/검증 분할에서 모든 긍정적인 예를 계속 유지하면서 노트북 메모리 예산 내에서 전체 다중 클러스터 기능 저장소에서 학습할 수 있습니다. 기본 한도는 다음과 같습니다.

- `BORG_XGB_MAX_TRAIN_ROWS=8000000`
- `BORG_XGB_MAX_VALID_ROWS=2000000`

해당 단계를 처음 실행하기 전에 repo-local Python 런타임을 한 번 설치하십시오.

```bash
./scripts/setup_advanced_runtime.sh
```

행동 참고 사항 다운로드:

- 기본 클러스터는 `b`부터 `g`까지입니다.
- `sample` 모드는 `events`, `usage` 및 `machines` 각각에 대해 `000000000000` 샤드를 다운로드합니다.
- `target_bytes` 모드는 일관성 있는 클러스터 조각을 구축합니다. 즉, 클러스터의 모든 머신 샤드, 해당 클러스터의 모든 이벤트 샤드, 동일한 클러스터의 사용 샤드를 구축합니다.
- `target_bytes`은 원시 데이터 디렉터리가 `target`과 `target + tolerance` 사이에 있을 때 사용 샤드를 마친 후에만 중지됩니다.
- `fixed_shards` 모드는 클러스터당 하나의 머신 샤드와 첫 번째 `N` 이벤트 샤드, 첫 번째 `N` 사용 샤드를 다운로드합니다. 여기서 `N=BORG_DOWNLOAD_SHARD_COUNT`
- `all` 모드는 선택한 클러스터에 대해 일치하는 모든 원시 샤드를 다운로드합니다.
- 새로운 다중 샤드 파일은 `cluster_type-<shard>.json.gz`로 저장됩니다(예: `b_usage-000000000170.json.gz`).
- 실용적인 `50–150 GB` 밴드는 `BORG_TARGET_RAW_BYTES=100000000000`, `BORG_TARGET_TOLERANCE_BYTES=50000000000`로 표현 가능

`b`부터 `g`까지 클러스터에 대해 결합된 창별 데이터 세트를 구축하려면 다음을 수행하세요.

```bash
python scripts/make_dataset.py
```

다중 샤드 원시 다운로드가 있는 경우 이제 플래트너는 `~/Documents/borg_processed/flat_shards/<kind>/<cluster>/` 아래에 샤드 Parquet 파일을 작성하고 데이터 세트 빌더는 해당 샤드 디렉터리를 직접 읽습니다.

고급 작업 영역에서 해당 경로는 `~/Documents/borg_xgboost_workspace/processed/flat_shards/<kind>/<cluster>/`입니다.

결합된 데이터세트에서 예측자 훈련 데이터세트를 구축하려면 다음 안내를 따르세요.

```bash
python scripts/make_forecaster_dataset.py
```

예측 빌더는 작업의 최종 터미널 이벤트가 기본 실패 세트 `2,3,6`에 있고 사용 기간이 끝난 후 다음 15분 이내에 발생하면 행에 긍정적인 레이블을 지정합니다.
또한 CPU 및 메모리 사용/활용에 대한 1단계 지연, 1단계 델타, 3창 롤링 수단과 같은 작업 기록 시간적 특성을 작성합니다.

로컬 클라우드 어댑터가 대상으로 지정할 수 있는 플랫폼에 구애받지 않는 표준 스키마로 해당 데이터세트를 내보내려면 다음을 수행하세요.

```bash
python scripts/export_common_forecaster_dataset.py
```

해당 내보내기는 기본적으로 `~/Documents/borg_processed/datasets/forecaster/common_forecaster` 아래에 클러스터 Parquet 파일을 작성합니다.
정식 스키마는 Borg 특정 열 이름에 의존하지 않고 워크로드 ID, 노드 ID, 창 타이밍, 관찰/요청된 CPU 및 메모리, 임시 기능, 오류 레이블과 같은 안정적인 필드를 유지합니다.

로컬 클라우드 원격 측정에서 동일한 표준 스키마를 빌드하려면 parquet parquet 또는 CSV 파일과 열 매핑 JSON 파일을 준비하고 다음을 실행합니다.

```bash
python scripts/build_local_common_forecaster_dataset.py \
  --input ~/Documents/local_cloud/telemetry.parquet \
  --output ~/Documents/local_cloud/common_forecaster.parquet \
  --mapping config/local_common_forecaster.example.json \
  --source-platform local_cloud
```

[`config/local_common_forecaster.example.json`](/Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator/config/local_common_forecaster.example.json)의 예제 매핑 파일은 예상되는 `canonical_name -> raw_column` 구조를 보여줍니다.

첫 번째 Polars 전용 예측 기준선을 훈련하고 평가하려면 다음을 수행하십시오.

```bash
python scripts/train_forecaster_baseline.py
```

트레이너는 `BORG_BASELINE_PROFILE`을 통해 명명된 기능 프로필을 지원합니다.

- `base`은 가장 강력한 평균 정밀도 기준을 유지하며 기본값입니다.
- `base_plus_roll`은 롤링 평균 시간 기능을 추가하고 최고 위험 경고 슬라이스를 개선합니다.
- `temporal_full`은 더 광horizon한 실험을 위해 지연, 델타 및 롤링 시간적 기능을 추가합니다.

예:

```bash
BORG_BASELINE_PROFILE=base_plus_roll \
BORG_BASELINE_DIR=~/Documents/borg_processed/datasets/forecaster/baseline_base_plus_roll \
python scripts/train_forecaster_baseline.py
```

기본 트레이너는 다음과 같이 씁니다.

- `metrics.json`
- `weights.json`
- `cluster_metrics.json`
- `feature_ranking.json`
- `validation_predictions.parquet`
- `top_risk_alerts.parquet`

기본적으로 `~/Documents/borg_processed/datasets/forecaster/baseline` 아래에 있습니다.

## 파이썬 환경

PyCharm에서 프로젝트-로컬 가상 환경을 사용하고 저장소 메타데이터에서 종속성을 설치합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
