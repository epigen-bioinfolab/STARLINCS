# **STARLINCS**

> **Signature-driven Transcriptome Alignment for Repurposing**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20MacOS%20%7C%20Windows-lightgrey)
[![GitHub release](https://img.shields.io/github/v/release/epigen-bioinfolab/CHROMACS)](https://github.com/epigen-bioinfolab/CHROMACS/releases)

  </div>
</div>

## About


STARLINCS ranks drugs by the similarity (or reversal) between a user-supplied gene expression signature and reference chemical-perturbation signatures, using a Gene Set Enrichment Analysis-based approach. It is available both as a **Graphical User Interface** and a **Command Line Interface**.


## Features

- **Two modes**
  - `reverse` — rank drugs that reverses the transcriptomic signature (e.g. for drug repurposing against a disease signature)
  - `mimic` — rank drugs that reproduce your signature (e.g. for identifying mode of action of novel compounds)
- **Tissue-specific reference presets**: bone, breast, cervix, central nervous system, haematopoietic and lymphoid tissue, kidney, large intestine, liver, lung, pancreas, placenta, prostate, skin, soft tissue — or supply your own reference CSV
- **Graphical User Interface** built with Tkinter for interactive use
- **Command Line Interface** for batch/scripted analysis
- Optional export of leading-edge genes for top-ranked drugs
