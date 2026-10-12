import os
import sys
import logging
import tempfile
import time
import zipfile

import pandas as pd
import numpy as np
import gseapy as gp

logger = logging.getLogger("starlincs.pipeline")

# ── Resource paths ─────────────────────────────────────────────────────────────
_RESOURCES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources",
)

METADATA_FILE    = os.path.join(_RESOURCES, "metadata.csv")


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_and_filter_genes(gene_file: str, master_genes: set, max_size: int) -> list[str]:
    """Load a gene list, keep only genes present in the master universe, trim to max_size."""

    logger.debug("Loading user gene list from: %s", gene_file)
    with open(gene_file, "r") as fh:
        genes = [line.strip().upper() for line in fh if line.strip()]

    before = len(genes)
    filtered = [g for g in genes if g in master_genes]
    trimmed  = filtered[:max_size]

    logger.info(
        "  Gene file %-40s  raw=%d  matched=%d  after_trim=%d",
        os.path.basename(gene_file), before, len(filtered), len(trimmed),
    )

    not_found = [g for g in genes if g not in master_genes]
    if not_found:
        logger.debug("  Genes not in master universe (%d): %s", len(not_found), ", ".join(not_found[:20]))

    return trimmed

def create_temp_gmt(gene_list: list[str], set_name: str) -> str:
    """Write a single-line GMT file to a temp location and return its path."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".gmt", delete=False)
    tmp.write("\t".join([set_name, "NA"] + gene_list) + "\n")
    tmp.close()
    logger.debug("Temp GMT for '%s': %s  (%d genes)", set_name, tmp.name, len(gene_list))
    return tmp.name


def _run_gsea_for_drug(drug: str, ranked_df: pd.DataFrame, gmt_path: str,
                        nperm: int, seed: int, min_size: int, max_size: int) -> pd.DataFrame:
    """Run gseapy.prerank for a single drug; return res2d with a DRUG column."""
    pre_res = gp.prerank(
        rnk=ranked_df[["gene_symbol", drug]],
        gene_sets=gmt_path,
        outdir=None,
        format=None,
        graph_num=0,
        permutation_num=nperm,
        weight=0,
        seed=seed,
        min_size=min_size,
        max_size=max_size,
    )
    res = pre_res.res2d.copy()
    res["DRUG"] = drug
    return res


def _run_gsea_loop(drugs: list[str], ranked_df: pd.DataFrame, gmt_path: str,
                   label: str, nperm: int, seed: int,
                   min_size: int, max_size: int) -> list[pd.DataFrame]:
    """
    Iterate over all drugs for one gene-set direction (UP or DOWN).
    Logs per-drug progress and skips drugs that raise exceptions.
    """
    results = []
    total   = len(drugs)
    failed  = []

    logger.info("  Running GSEA for %s gene set (%d drugs) …", label, total)

    for i, drug in enumerate(drugs, start=1):
        t0 = time.time()
        try:
            res = _run_gsea_for_drug(drug, ranked_df, gmt_path,
                                      nperm, seed, min_size, max_size)
            elapsed = time.time() - t0
            logger.debug("    [%d/%d] %-40s  %.2fs", i, total, drug, elapsed)
            results.append(res)
        except Exception:
            logger.warning("    [%d/%d] SKIPPED %-36s — see traceback below",
                           i, total, drug, exc_info=True)
            failed.append(drug)

    if failed:
        logger.warning("  %s loop: %d drug(s) failed and were skipped: %s",
                       label, len(failed), ", ".join(failed))
    else:
        logger.info("  %s loop: all %d drugs completed successfully.", label, total)

    return results


# ── Main pipeline ──────────────────────────────────────────────────────────────

def run_pipeline(
    reference: str,
    up_file: str,
    down_file: str,
    output: str,
    mode: str = "reverse",
    seed: int = 1234,
    max_size: int = 500,
    min_size: int = 20,
    leading_genes_n: int | None = None,
    nperm: int = 1000,
) -> pd.DataFrame:

    pipeline_start = time.time()
    up_gmt = down_gmt = None   # track temp files for cleanup

    try:
        # ── 1. Load reference matrix ──────────────────────────────────────────
        logger.info("── Step 1/5  Loading reference matrix: %s", reference)
        t0 = time.time()
        drugs_ranked = pd.read_csv(reference, header=0, index_col=False)
        gene_col     = drugs_ranked.columns[0]
        drugs_ranked = drugs_ranked.rename(columns={gene_col: "gene_symbol"})
        master_genes = set(drugs_ranked["gene_symbol"].dropna().str.strip().str.upper())
        drug_list    = [c for c in drugs_ranked.columns if c != "gene_symbol"]

        logger.info(
            "  Reference loaded in %.2fs  |  genes=%d  drugs=%d",
            time.time() - t0, len(drugs_ranked), len(drug_list),
        )

        # ── 2. Gene filtering ─────────────────────────────────────────────────
        logger.info("── Step 2/5  Gene filtering")
        up_genes   = load_and_filter_genes(up_file,   master_genes, max_size)
        down_genes = load_and_filter_genes(down_file, master_genes, max_size)

        if not up_genes:
            raise ValueError("No up-regulated genes survived filtering — check your gene symbols.")
        if not down_genes:
            raise ValueError("No down-regulated genes survived filtering — check your gene symbols.")

        up_gmt   = create_temp_gmt(up_genes,   "UP_GENES")
        down_gmt = create_temp_gmt(down_genes, "DOWN_GENES")

        # ── 3. Load metadata ──────────────────────────────────────────────────
        logger.info("── Step 3/5  Loading metadata: %s", METADATA_FILE)
        metadata = pd.read_csv(METADATA_FILE)
        meta_slim = (
            metadata[["cmap_name", "target", "moa", "canonical_smiles",
                       "inchi_key", "compound_aliases", "groups"]]
            .drop_duplicates(subset="cmap_name")
        )
        logger.info("  Metadata rows: %d", len(meta_slim))

        # ── 4. GSEA loops ─────────────────────────────────────────────────────
        logger.info("── Step 4/5  GSEA  (nperm=%d  seed=%d  min=%d  max=%d)",
                    nperm, seed, min_size, max_size)

        t0       = time.time()
        up_rows  = _run_gsea_loop(drug_list, drugs_ranked, up_gmt,
                                   "UP",   nperm, seed, min_size, max_size)
        dn_rows  = _run_gsea_loop(drug_list, drugs_ranked, down_gmt,
                                   "DOWN", nperm, seed, min_size, max_size)
        gsea_elapsed = time.time() - t0

        if not up_rows:
            raise RuntimeError("GSEA produced no results for the UP gene set — all drugs failed.")
        if not dn_rows:
            raise RuntimeError("GSEA produced no results for the DOWN gene set — all drugs failed.")

        logger.info("  GSEA finished in %.2fs", gsea_elapsed)

        # ── 5. Merge, score, output ───────────────────────────────────────────
        logger.info("── Step 5/5  Merging and scoring")

        up_df = pd.concat(up_rows, ignore_index=True)
        dn_df = pd.concat(dn_rows, ignore_index=True)

        up_df = up_df[["DRUG", "NES", "Lead_genes"]].rename(
            columns={"NES": "NES_up", "Lead_genes": "lead_genes_up"})
        dn_df = dn_df[["DRUG", "NES", "Lead_genes"]].rename(
            columns={"NES": "NES_down", "Lead_genes": "lead_genes_dn"})

        merged = pd.merge(up_df, dn_df, on="DRUG")
        merged["connectivity_score"] = merged["NES_down"] - merged["NES_up"]

        merged = (
            merged
            .merge(meta_slim, left_on="DRUG", right_on="cmap_name", how="left")
            .drop(columns="cmap_name")
        )

        merged = merged.rename(columns={
            "DRUG":               "drug",
            "NES_up":             "NES_up",
            "NES_down":           "NES_dn",
            "connectivity_score": "connectivity_score",
            "compound_aliases":   "alias",
        })

        cols_full   = ["drug", "target", "moa", "groups",
                       "NES_up", "NES_dn", "connectivity_score",
                       "alias", "canonical_smiles", "inchi_key",
                       "lead_genes_up", "lead_genes_dn"]
        cols_output = ["drug", "target", "moa", "groups",
                       "NES_up", "NES_dn", "connectivity_score",
                       "alias", "canonical_smiles", "inchi_key"]

        merged     = merged[cols_full]
        output_df  = merged[cols_output]

        ascending  = (mode == "reverse")
        output_df  = output_df.sort_values("connectivity_score", ascending=ascending)

        logger.info("  Mode: %s — sorted %s by connectivity_score",
                    mode, "ascending" if ascending else "descending")
        logger.info("  Result rows: %d", len(output_df))

        # ── Write output ──────────────────────────────────────────────────────
        ext = os.path.splitext(output)[-1].lower()

        if ext in (".csv", ".tsv", ".txt"):
            sep = "\t" if ext in (".tsv", ".txt") else ","
            os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
            output_file = output
            output_dir  = os.path.dirname(output) or "."
            output_df.to_csv(output_file, index=False, sep=sep)

        elif ext in (".xlsx", ".xls"):
            os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
            output_file = output
            output_dir  = os.path.dirname(output) or "."
            output_df.to_excel(output_file, index=False, engine="openpyxl")

        else:
            os.makedirs(output, exist_ok=True)
            output_file = os.path.join(output, "STARLINCS_results.xlsx")
            output_dir  = output
            output_df.to_excel(output_file, index=False, engine="openpyxl")

        logger.info("  Results saved to: %s", output_file)

        # ── Leading genes zip ─────────────────────────────────────────────────
        if leading_genes_n is not None:
            top_names = output_df.head(leading_genes_n)["drug"].tolist()
            top_drugs = merged.set_index("drug").loc[top_names].reset_index()
            zip_path  = os.path.join(output_dir, "leading_genes.zip")

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for _, row in top_drugs.iterrows():
                    safe = row["drug"].replace(" ", "_").replace("/", "-")
                    zf.writestr(f"{safe}_leading_genes_up.txt",
                                str(row["lead_genes_up"]).replace(";", "\n"))
                    zf.writestr(f"{safe}_leading_genes_dn.txt",
                                str(row["lead_genes_dn"]).replace(";", "\n"))

            logger.info("  Leading genes for top %d drugs saved to: %s",
                        leading_genes_n, zip_path)

    finally:
        # Always remove temp GMT files, even if the pipeline crashed mid-way
        for path in (up_gmt, down_gmt):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                    logger.debug("Cleaned up temp GMT: %s", path)
                except Exception:
                    logger.warning("Could not delete temp GMT file: %s", path)

    logger.info("Pipeline completed in %.2fs", time.time() - pipeline_start)
    return output_df
