# Scripts: Hybrid Path Planning Algorithms for Mobile Robots and Autonomous Vehicles: A Systematic Mapping Study

Python scripts used to build the map of 2,695 hybrid path-planning studies and to produce every count, table and figure in the paper and in Supplementary Material S3 and S5.

Authors: Zubaidah B. Alalwani and Waleed Al-Ashtari, College of Artificial Intelligence, University of Baghdad.

The scripts read the coded data (`data/`) and the search records (`search/`), which are released with the paper's data package. To run them, place this folder's contents in the root of that package.

## Requirements

Python 3.10 or later, then:

```bash
pip install -r requirements.txt
```

## Reproduce all results

```bash
python tools/build_all.py
```

This runs, in order: the map, the class profile, the example studies, the evaluation and moving-obstacle profile, the sensitivity analyses, all figures, and the update of S3.

## Scripts

### Search and screening (`tools/`)

| Script | Purpose |
|---|---|
| `merge_dedupe.py` | Merges the database exports and removes duplicates (by DOI, then by title, year and first author), logging every removed record |
| `make_pair_queries.py` | Builds the 15 Scopus component-pair queries (S2) |
| `make_screening_batches.py` | Splits the records into title-and-abstract screening workbooks |
| `screening_reconcile.py` | Merges screening decisions into one file |
| `make_fulltext_workbooks.py` | Builds the full-text assessment workbooks |
| `make_classification_workbooks.py` | Builds the classification workbooks |

### Analysis (`tools/`)

| Script | Purpose |
|---|---|
| `build_all.py` | Runs the whole analysis in order |
| `build_mapped.py` | Builds `data/mapped_studies.csv` (the 2,695 mapped studies) from the classification file |
| `class_profile.py` | Profile of each hybrid class (Table 6) |
| `evaluation_profile.py` | Moving-obstacle handling and evaluation terms named in titles and abstracts (Table 7; S5, Tables S5-S6) |
| `sensitivity.py` | Sensitivity analyses: full-text set versus abstract set (Table 8, Figure 7) and fuzzy logic placed in F3 instead of F6 |
| `select_examples.py` | Selects the example studies by the fixed rule (S5, Tables S3-S4) |
| `update_s3.py` | Refreshes the data sheets of S3 |
| `check_submission.py` | Lists unresolved placeholders in the manuscript and checks that every example study is a mapped full-text study |

### Figures (`figures/`)

| Script | Figure |
|---|---|
| `fig2_taxonomy.py` | Figure 1: taxonomy of method families and hybrid classes |
| `fig1_prisma.py` | Figure 2: flow diagram (PRISMA 2020 structure) |
| `fig3_per_year.py` | Figure 3: studies per year |
| `fig4_cooccurrence.py` | Figure 4: family co-occurrence |
| `fig6_type_platform.py` | Figure 5: hybrid class by platform |
| `fig7_static_dynamic.py` | Figure 6: static and dynamic evaluation environments |
| `fig8_sets.py` | Figure 7: full-text set versus abstract set |
| `fig5_type_metric.py` | S5, Figure S1: integration strategy and planning level by class |
| `_common.py` | Shared data loader |

The file names follow the order in which the figures were first drawn, so they do not match the figure numbers of the paper; the table above gives the mapping.

### Tables

| Script | Purpose |
|---|---|
| `tables/make_examples_table.py` | LaTeX table of the example studies |

## Licence

MIT (see `LICENSE`).
