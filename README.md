<p align="left">
  <img src="resources/for_github.png" width="160" alt="STARLINCS logo"/>
</p>

# STARLINCS

**S**ignature-driven **T**ranscriptome **A**lignment for **R**epurposing via **LINCS**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
[![GitHub release](https://img.shields.io/github/v/release/epigen-bioinfolab/STARLINCS)](https://github.com/epigen-bioinfolab/STARLINCS/releases)

## Overview

STARLINCS helps researchers find therapeutic candidates by comparing a transcriptomic gene signature against a reference library of drug perturbation profiles. You provide up- and down-regulated genes, and STARLINCS uses Gene Set Enrichment Analysis (GSEA) to calculate a connectivity score for each reference drug. The output is a ranked list of drugs by their ability to **mimic** or **reverse** your signature.

STARLINCS is available as both a **Graphical User Interface (GUI)** for routine use at the bench and a **Command-Line Interface (CLI)** for scripted analysis and HPC pipelines.

**Two ways to use it**

| Mode | Use it when you want to… | Example |
|---|---|---|
| `reverse` | Find drugs that **oppose** your signature | Drug repurposing against a disease signature (e.g. fibrotic vs. healthy lung) |
| `mimic` | Find drugs that **reproduce** your signature | Surfacing compounds with a desired effect, or inferring the mode of action of a novel compound |

## Features

- **Organ-specific reference presets** built from LINCS L1000 consensus signatures, or bring your own reference CSV
- **GUI and CLI** with the same parameters in both
- **Mimic / reverse** ranking in a single run
- **Leading-edge genes** exported per drug (GUI) or for the top N drugs (CLI)
- **Batch-friendly**: easy to loop over many signatures in a bash script
- Results exported as `.csv`, `.tsv` or Excel

## System Requirements

| Requirement | Details |
|---|---|
| Operating system | Windows, Linux, or macOS |
| Python | 3.9 or higher |
| Memory | 4 GB RAM recommended |
| Disk space | ~800 MB |

Dependencies (`pandas`, `gseapy`, `numpy`, `tkinter` for the GUI) are installed automatically by the installer. On macOS, the installer also sets up Rust, since `gseapy` has no pre-built wheel there.

## Installation

### Windows

1. Check your Python version in Command Prompt (`Win` + `R`, type `cmd`):
   ```bat
   python --version
   ```
   If Python is missing or older than 3.9, install it from [python.org](https://www.python.org/).
   > **Important:** during installation, tick **"Add python.exe to PATH"** before clicking **Install Now**.

2. Download the Windows version:
   [**Download STARLINCS for Windows**](https://github.com/epigen-bioinfolab/STARLINCS/archive/refs/heads/starlincs-for-windows.zip)

3. Extract the `.zip` file to a convenient location.
4. Double-click the **setup** file to run the installer.
5. Once installation finishes, open the STARLINCS folder and double-click the **`LAUNCH_STARLINCS`** VBScript file (or the desktop shortcut) to start the GUI.

### Linux

```bash
git clone https://github.com/epigen-bioinfolab/STARLINCS
cd STARLINCS
chmod +x install.sh && ./install.sh
```

Or download the source instead of cloning:

```bash
wget https://github.com/epigen-bioinfolab/STARLINCS/archive/refs/heads/main.zip
unzip main.zip
cd STARLINCS-main
chmod +x install.sh && ./install.sh
```

Verify the installation:

```bash
starlincs --version
```

> **Windows Subsystem for Linux (WSL):** follow the Linux steps above and run every command from the WSL terminal, not from Command Prompt or PowerShell.

### macOS

The steps are the same as on Linux:

```bash
git clone https://github.com/epigen-bioinfolab/STARLINCS
cd STARLINCS
chmod +x install.sh && ./install.sh
starlincs --version
```

(Alternatively, download and unzip `main.zip` as shown in the Linux section.) The installer takes care of Rust, which `gseapy` needs on macOS.

## Quick Start

### Graphical User Interface

Launch it:

- **Windows:** double-click `LAUNCH_STARLINCS` or the desktop shortcut
- **Linux / macOS:**
  ```bash
  starlincs gui
  ```

Then:

1. **Select reference:** choose an organ under *Select Organ*, or click *Upload CSV* under *Custom Reference*.
2. **Insert genes:** click *Upload .txt* under *Upregulated Genes* and *Downregulated Genes*, or paste gene names directly into the input boxes.
3. **Adjust parameters** (optional): *Min Gene*, *Max Gene*, *Seed*, *Permutations*.
4. **Choose mode:** *Mimic* or *Reverse*.
5. Run the analysis, review the results table, and use *Export CSV* to save the full ranking. Leading genes can be exported per drug from the results table.

### Command-Line Interface

**Linux / macOS**

```bash
starlincs run \
    --reference lung \
    --up /path/to/up_genes.txt \
    --down /path/to/down_genes.txt \
    --mode mimic \
    --output /path/to/results.csv
```

**Windows (Command Prompt)**

```bat
starlincs run ^
    --reference lung ^
    --up /path/to/up_genes.txt ^
    --down /path/to/down_genes.txt ^
    --mode mimic ^
    --output /path/to/results.csv
```

## Input Files

**Gene lists.** Provide one plain-text file for upregulated genes and one for downregulated genes: one gene symbol per line, no header, no extra columns.

```
MAP2
LINC01564
TUBA3E
MYL2
...
```

These are typically obtained from a differential expression analysis (e.g. DESeq2 or limma) with commonly used thresholds of adjusted p-value < 0.05 and |log2FC| > 1. Order each list by fold change.

**Reference.** Pick a built-in organ reference or supply your own CSV.

Built-in references: `bone`, `breast`, `cervix`, `cns`, `haematopoietic_and_lymphoid_tissue`, `kidney`, `large_intestine`, `liver`, `lung`, `pancreas`, `prostate`, `skin`

> Reference names are case-sensitive (use `lung`, not `Lung`). Run `starlincs --help` to see the valid list.

A custom reference must be a CSV where the first column (`Gene`) holds HGNC gene symbols and each remaining column is one drug's ranked list. Values are the gene's rank for that drug, from most upregulated (rank 1) to most downregulated (highest rank).

| Gene | erlotinib | vemurafenib | tamoxifen | … | sunitinib |
|---|---|---|---|---|---|
| TP53 | 234 | 7635 | 2313 | … | 8987 |
| ERBB2 | 4565 | 6787 | 23 | … | 11323 |
| INS | 2343 | 4532 | 2364 | … | 1232 |
| … | … | … | … | … | … |

## Parameters

| CLI argument | GUI field | Required | Default | Description |
|---|---|---|---|---|
| `--reference` | Select Organ | **Yes** | – | Built-in organ name (e.g. `lung`) or path to a custom reference CSV |
| `--up` | Upregulated Genes | **Yes** | – | File of upregulated genes, one per line |
| `--down` | Downregulated Genes | **Yes** | – | File of downregulated genes, one per line |
| `--mode` | Mimic / Reverse | **Yes** | – | `mimic` or `reverse` |
| `--output` | Export CSV | **Yes** | – | Directory or filename (`.csv`, `.tsv`, or `.xls`) for the results |
| `--min-gene` | Min Gene | No | `20` | Minimum genes required for a gene set to be analysed |
| `--max-gene` | Max Gene | No | `500` | Maximum genes allowed for a gene set to be analysed |
| `--seed` | Seed | No | `1234` | Random seed for reproducible permutations |
| `--nperm` | Permutations | No | `1000` | Number of permutations. 100 is enough for quick testing; use more for final analyses |
| `--include-leading-genes N` | Results page | No | None | Export leading-edge genes for the top *N* drugs as a `.zip` alongside the results |

## Batch Analysis

To run many signatures, arrange paired up/down files in one folder:

```
signatures/
├── sample1_up.txt
├── sample1_down.txt
├── sample2_up.txt
├── sample2_down.txt
└── ...
```

Then loop over them (`run_batch.sh`):

```bash
#!/bin/bash
for i in $(seq 1 40); do
    starlincs run \
        --reference lung \
        --up signatures/sample${i}_up.txt \
        --down signatures/sample${i}_down.txt \
        --mode mimic \
        --output results/sample${i}_results.csv
done
```

```bash
chmod +x run_batch.sh && ./run_batch.sh
```

Each signature is processed in turn and saved as its own `.csv` in `results/`.

## Output

| Column | Description |
|---|---|
| `drug` | Drug/compound name from the reference library |
| `target` | Known molecular target(s) |
| `moa` | Mechanism of action |
| `groups` | Approval status: approved, investigational, experimental, or vet_approved |
| `NES_up` | Normalized Enrichment Score for the upregulated gene list |
| `NES_dn` | Normalized Enrichment Score for the downregulated gene list |
| `connectivity_score` | `NES_dn − NES_up`; used to rank drugs according to the selected mode |
| `alias` | Alternative drug name recorded in LINCS |
| `canonical_smiles` | Canonical SMILES of the chemical structure |
| `inchi_key` | InChIKey, for cross-referencing other chemical databases |

Other files produced:

- `<drug_name>_leading_genes.zip`: leading-edge up/down gene lists (GUI export per drug, or CLI `--include-leading-genes N`)
- `starlincs.log`: detailed session log, written to the current working directory

> The GUI results table shows the **top 100 candidates**, while **Export CSV** saves the **full** ranked list.

## How It Works

STARLINCS uses the **GSEA Prerank** method. Your up- and down-regulated gene sets are tested against each drug's ranked gene list. The gene set is "walked" down the list, increasing a running sum when a gene matches and decreasing it otherwise; the peak deviation is the Enrichment Score (ES). Permutation testing (`--nperm`) then yields a Normalized Enrichment Score (NES), which allows fair comparison across drugs. NES is computed separately for the up (`NES_up`) and down (`NES_dn`) sets and combined into the final connectivity score.

**Why a consensus reference?** LINCS holds over 1 million perturbation signatures, which is expensive to query directly, and the L1000 assay produces considerable variability between signatures of the same drug. STARLINCS builds its references as follows:

1. **Stratification by organ of origin:** signatures are grouped by the tissue origin of their cell lines.
2. **Density-based clustering:** within each subset, consistent signatures are kept and noisy profiles are filtered out.
3. **Rank aggregation:** all reliable signatures for a drug are aggregated into one prototype ranked list.

## Troubleshooting

| Problem | Solution |
|---|---|
| `"Python is not recognized"` | Python is not installed or not on PATH. Reinstall from [python.org](https://www.python.org/) and tick **"Add Python to PATH"**. |
| `python --version` shows a version below 3.9 | Install Python 3.9 or newer, or update your existing installation. |
| `"Reference not found"` | Check that `--reference` matches a built-in name exactly (case-sensitive, e.g. `lung`). Run `starlincs --help` for the list. |
| Gene file not recognized | Save up/down lists as plain `.txt`, one gene per line, with no header row or extra columns. |

## Contact

For bugs, questions or feature requests, please [open an issue](https://github.com/epigen-bioinfolab/STARLINCS/issues).

- Lab website: [www.epigen-bioinfolab.com](https://www.epigen-bioinfolab.com/)
- Email: epigen.bioinfolab@gmail.com
- Corresponding author: khademul@du.ac.bd

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
