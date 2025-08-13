# af2pdb

AlphaFold/ColabFold 결과와 템플릿 구조를 이용해 결손(loop) 구간을 보수하고,
HHsearch 템플릿 밸런싱 단계까지 포함한 파이프라인 예시.

## 환경 설치
```bash
bash env_setup/install_env.sh
conda activate af2pdb
```
* `hhsuite`(hhblits, hhsearch), `openmm`, `gemmi`, `biopython` 등을 conda로 설치합니다.
* ColabFold는 별도 설치가 필요할 수 있습니다. (`pip install 'colabfold[alphafold]'` 등)

## 디렉토리
```
af2pdb/
├── env_setup/
│   └── install_env.sh
├── preprocessing/
│   ├── pdb_to_mmcif_and_renumber.py
│   ├── mask_template.py
│   └── make_window_fasta.py
├── colabfold/
│   └── run_af2.py
├── balancing/
│   ├── run_hhsearch.py
│   └── select_templates.py
├── postprocessing/
│   ├── blend_with_template.py
│   ├── graft_and_minimize.py
│   └── quality_check.py
└── scripts/
    └── run_pipeline.sh
```

## 워크플로우 개요
1) 전처리: 템플릿 정리(mmCIF 변환·리넘버링, 결손 구간 마스킹), 윈도우 FASTA 생성  
2) 1차 추론: ColabFold (템플릿 OFF)  
3) 밸런싱: HHblits→HHsearch로 템플릿 후보 검색, Top-N 목록 생성  
4) 2차 추론: ColabFold (템플릿 ON)  
5) 그래프팅+최소화: 예측 루프를 템플릿 구간에 덮어쓰기 후 OpenMM 최소화  
6) 품질 리포트: pLDDT/PAE/클래시 요약

## 사용 예시(일괄 실행 스크립트)
`scripts/run_pipeline.sh`를 열어 경로/파라미터를 수정한 뒤 실행하세요.
```bash
bash scripts/run_pipeline.sh
```

## 좌표 블렌딩(선택)
템플릿(T)과 예측(P)을 특정 구간에서 `X = (1-α)T + αP`로 섞고 싶다면:
```bash
python postprocessing/blend_with_template.py \
  --template template_masked.cif \
  --pred runs/af2_r2/*rank_001*.pdb \
  --out blended.pdb \
  --ranges "A:100-130" \
  --alpha 0.35
```

## 주의사항
- HHsuite DB 경로는 로컬에 맞게 지정하세요. 예) `uniclust30_2018_08`, `pdb70` 등.
- `colabfold_batch`의 템플릿 디렉토리 직접 지정은 버전에 따라 지원이 다릅니다. 기본적으로 `--use-templates`로 내부 파이프라인을 사용하세요.
- `graft_and_minimize.py`의 매핑 길이는 일치해야 합니다. 번호 미스매치 시 에러가 발생합니다.
- OpenMM 최소화는 진공(NoCutoff)에서 간단히 수행합니다. 필요 시 cutoff/solvent/제약 조건을 조정하세요.
