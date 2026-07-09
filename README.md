# README
## A Graphene Oxide/PEDOT:PSS Microwave Antenna Electronic Nose for Selective Detection of Strawberry Aroma Volatiles and Freshness Classification

**Abstract**

Post-harvest losses account for an estimated 14\% of global food production, with soft fruits disproportionately affected by the lack of scalable, non-destructive monitoring tools. Among these, strawberries are the highest-value soft fruit crop. However, their ripening and post-harvest freshness evolution are difficult to assess non-invasively, as aromatic maturity does not track visual colour, and the ester-rich strawberry volatilome lies outside the selectivity range of dominant metal oxide semiconductor sensors. To address this, we demonstrate a Graphene Oxide/Poly(3,4-ethylenedioxythiophene) polystyrene sulfonate (GO/PEDOT:PSS) composite antenna sensor as a per- and poly-fluoroalkyl substances (PFAS)-free solution, evaluating the device across a ten-compound volatile library and on whole-fruit strawberry headspace. The proposed sensor achieved classification accuracy of ten representative strawberry volatile organic compounds (VOCs) over 96\% under leave-one-concentration-out cross-validation. Applied to whole-fruit headspace, binary freshness classification on unseen batches reached a Receiver Operating Characteristic Area Under the Curve (ROC AUC) score of 0.88 and classification accuracy of 78\% under leave-one-batch-out cross-validation. These results are a promising step toward freshness discrimination under representative field conditions of real-world scenarios and batch-to-batch variability.


The repository is organised as two trials:

| Trial                                               | Task                                                        | Data                                    |
|-----------------------------------------------------|-------------------------------------------------------------|-----------------------------------------|
| [`trial_01`](#trial-01--voc-identification)         | Identify one of 10 VOCs, estimate concentration             | 10 analytes, ~4,200 sweeps each         |
| [`trial_02`](#trial-02--food-freshness-estimation)  | Predict days-to-best-before, classify as fresh/not-fresh    | Real food headspace, 5 acquisition days |

`trial_01` establishes that the two sensors produce separable, learnable
signatures on discrete analytes; `trial_02` applies the device to real food headspace.

---

## Trial 01: VOC Identification / Concentration Estimation

Bench characterisation on a panel of ten volatile organic compounds
(alcohols and esters), dosed in microlitre steps.

| Folder | Compound    | Class   |     | Folder   | Compound         | Class   |
|--------|-------------|---------|-----|----------|------------------|---------|
| `MeOH` | Methanol    | alcohol |     | `2-BuOH` | 2-Butanol        | alcohol |
| `EtOH` | Ethanol     | alcohol |     | `MeBu`   | Methyl butyrate  | ester   |
| `PrOH` | 1-Propanol  | alcohol |     | `EtBu`   | Ethyl butyrate   | ester   |
| `IPA`  | Isopropanol | alcohol |     | `MeHex`  | Methyl hexanoate | ester   |
| `BuOH` | 1-Butanol   | alcohol |     | `EtHex`  | Ethyl hexanoate  | ester   |

```
trial_01/
├── data/
│   ├── <ANALYTE>/                 # one folder per VOC, ~4,200 raw sweeps each
│   │   └── <dose>ul_CH<n>_S<xx>_<seq>_<timestamp>_S<sample>.csv
│   ├── environmental_data.csv     # ambient temp/humidity during collection
│   └── collector.py               # VNA datalogger
└── src/
    ├── 01_loading.ipynb           # parse CSVs → df_ch1/df_ch2.pkl → processed_data.pkl
    ├── 01_preliminary.ipynb       # PCA / LDA / t-SNE separability, noise floor
    ├── 01_classification.ipynb    # 10-class VOC identification
    ├── 01_regression.ipynb        # dose/concentration regression
    ├── 01_results.ipynb           # IEEE-styled figures & tables
    └── 01_results/                # exported figures
```

Filename encoding:

`0.0ul_CH1_S11_1_20250710_115951_S0001.csv`:
`0.0ul` dosed volume (µL) · `CH1`/`S11` channel & S-parameter (sensor A) ·
`20250710_115951` timestamp · `S0001` sample index within the dose step.

---

## Trial 02: Food-freshness Estimation

Estimation of `timedelta_days`, days remaining until best-before (regression),
plus a derived binary fresh/not-fresh label (binary classification).

```
trial_02/
├── data/
│   ├── 20260312/ 20260318/ 20260319/ 20260320/ 20260321/   # one folder per day
│   └── collector.py               # VNA datalogger
└── src/
    ├── 02_loading.ipynb           # parse raw sweeps → processed_data.pkl
    ├── 02_preliminary.ipynb       # noise floor, feature ablation, PCA/PLS/t-SNE
    ├── 02_regression.ipynb        # LOGO + K-fold regression → regression_results_v5.pkl
    ├── 02_results.ipynb           # IEEE-styled figures & tables
    └── 02_results/                # exported figures
```

Filename encoding:

Headspace sweeps over five acquisition days, grouped in directories by best-before date.
CSV files (e.g., `20260319/headspace_data_20260316_172940.csv`) containe timestamped data
in the format `trial_02/data/20260319/headspace_data_YYYYMMDD_HHMMSS.csv`.

---

## Notes

- Large artifacts (`processed_data.pkl`, `df_ch1.pkl`, `df_ch2.pkl`, ~0.1–1 GB)
  are regenerated by the loading notebooks and are not needed to view the
  results notebooks, which read only the small `*_results.pkl` files.

Generative AI tools were used to assist with code development and debugging of
the analysis pipeline in this repository.
The authors reviewed and verified all code, results, and conclusions.
No AI tools were involved in generating the research data itself.
