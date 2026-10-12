import argparse
import os
import sys
import platform
import subprocess
import logging
import time
import traceback

# ──────────────────────────────────────────────────────────────────────────────

LOG_FILE = os.path.join(os.getcwd(), "starlincs.log")

_file_fmt = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_con_fmt = logging.Formatter("%(message)s")

_fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
_fh.setLevel(logging.DEBUG)          # everything → file
_fh.setFormatter(_file_fmt)

_ch = logging.StreamHandler(sys.stdout)
_ch.setLevel(logging.INFO)           # clean console
_ch.setFormatter(_con_fmt)

# Attach to ROOT logger so gseapy / pandas warnings also land in the log
_root = logging.getLogger()
_root.setLevel(logging.DEBUG)
_root.addHandler(_fh)
_root.addHandler(_ch)

logger = logging.getLogger("starlincs.cli")


def _handle_uncaught(exc_type, exc_value, exc_tb):
    """Catch any exception that escapes main() and write it to the log."""
    if issubclass(exc_type, KeyboardInterrupt):
        logger.warning("Interrupted by user (KeyboardInterrupt).")
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.critical(
        "UNCAUGHT EXCEPTION — process will exit\n%s",
        "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
    )

sys.excepthook = _handle_uncaught


# ──────────────────────────────────────────────────────────────────────────────
# Imports that might fail (caught by the hook above)
# ──────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

try:
    from core.pipeline import run_pipeline
except Exception:
    logger.critical("Failed to import core.pipeline — see traceback below.", exc_info=True)
    sys.exit(1)


__version__ = "1.0.0"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def launch_gui() -> None:
    project_root = os.path.dirname(SCRIPT_DIR)

    if platform.system() == "Windows":
        venv_python = os.path.join(project_root, ".venv", "Scripts", "pythonw.exe")
        if not os.path.exists(venv_python):
            venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    else:
        venv_python = os.path.join(project_root, ".venv", "bin", "python")

    app_path = os.path.join(SCRIPT_DIR, "gui.py")
    logger.info("Launching GUI: %s %s", venv_python, app_path)
    subprocess.run([venv_python, app_path])


def existing_reference(ref: str) -> str:
    project_root = os.path.dirname(os.path.abspath(__file__))
    data_dir     = os.path.join(project_root, "data")

    preset_path = os.path.join(data_dir, f"{ref}.csv")
    if os.path.exists(preset_path):
        return preset_path
    if os.path.exists(ref):
        return os.path.abspath(ref)
    cwd_path = os.path.join(os.getcwd(), ref)
    if os.path.exists(cwd_path):
        return cwd_path

    presets = [f[:-4] for f in os.listdir(data_dir) if f.endswith(".csv")]
    raise FileNotFoundError(
        f"Reference not found: '{ref}'\n"
        f"  Tried preset : {preset_path}\n"
        f"  Tried path   : {os.path.abspath(ref)}\n"
        f"  Tried CWD    : {cwd_path}\n"
        f"  Available presets: {presets}"
    )


def _log_session_header(args_str: str) -> None:
    sep = "=" * 70
    logger.info(sep)
    logger.info("STARLINCS  v%s  —  New session", __version__)
    logger.info(sep)
    logger.info("Python       : %s", sys.version.split()[0])
    logger.info("Platform     : %s", platform.platform())
    logger.info("Working dir  : %s", os.getcwd())
    logger.info("Log file     : %s", LOG_FILE)
    logger.info("Command line : %s", args_str)
    logger.info(sep)


def _log_session_footer(elapsed: float, success: bool) -> None:
    sep = "=" * 70
    logger.info(sep)
    logger.info("Session ended  [%s]  in %.2f s", "SUCCESS" if success else "FAILED", elapsed)
    logger.info(sep)


# ──────────────────────────────────────────────────────────────────────────────
# Argument parser
# ──────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="starlincs",
        description=(
            "STARLINCS — Signature-driven Transcriptome Alignment for Repurposing\n"
            "----------------------------------------------------------------------\n"
            "Rank drugs by transcriptomic similarity or reversal."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Graphical User Interface:\n"
            "  starlincs gui\n\n"
            "Command-Line Interface:\n"
            "  starlincs run \\\n"
            "      --reference lung \\\n"
            "      --up up_genes.txt \\\n"
            "      --down down_genes.txt \\\n"
            "      --mode reverse \\\n"
            "      --min-gene 20 \\\n"
            "      --max-gene 500 \\\n"
            "      --seed 1234 \\\n"
            "      --nperm 1000 \\\n"
            "      --leading-genes 10\\\n"
            "      --output results.xls\n\n"
            "reference presets:\n"
            "  bone, breast, cervix, cns, haematopoietic_and_lymphoid_tissue,\n"
            "  kidney, large_intestine, liver, lung, pancreas, prostate, skin\n"
            "  starlincs --version\n\n"
            "  starlincs run --help\n\n"
        ),
    )
    parser.add_argument("--version", action="version", version=f"starlincs {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("gui", help="launch the graphical user interface")

    run_p = sub.add_parser(
        "run",
        help="run analysis from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    run_p.add_argument("--reference", required=True, metavar="PATH",
                       help="reference preset name (e.g. lung) or\n"
                       "path to a drug-gene CSV")
    run_p.add_argument("--up",   required=True, metavar="FILE",
                       help="plain-text file (.txt) of upregulated genes\n(HGNC symbol), one per line\n")
    run_p.add_argument("--down", required=True, metavar="FILE",
                       help="plain-text file (.txt) of downregulated genes\n(HGNC symbol), one per line\n")
    run_p.add_argument("--mode", choices=["mimic", "reverse"], required=True,
                       metavar="MODE",
                       help="reverse: rank drugs that reverses your transcriptome;"
                            "mimic: rank drugs that mimics your transcriptome\n")
    run_p.add_argument("--seed",     type=int, default=1234, metavar="N",
                       help="random seed (default: 1234)\n")
    run_p.add_argument("--nperm",    type=int, default=1000, metavar="N",
                       help="number of permutations (default: 1000)\n")
    run_p.add_argument("--max-gene", type=int, default=500,  metavar="N",
                       help="maximum genes per set (default: 500)\n")
    run_p.add_argument("--min-gene", type=int, default=20,   metavar="N",
                       help="minimum genes per set (default: 20)\n")
    run_p.add_argument("--output", required=True, metavar="DIR",
                       help="output directory; Result will be saved here or\na name with a '.csv', '.tsv', '.xls' extension\n")
    run_p.add_argument("--leading-genes", type=int, default=None, metavar="N",
                       help="export leading genes for top N drugs \nas a zip alongside results\n")
    return parser


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    start   = time.time()
    _log_session_header(" ".join(sys.argv))

    parser  = build_parser()
    args    = parser.parse_args()
    success = False

    try:
        if args.command == "gui":
            launch_gui()
            success = True

        elif args.command == "run":
            logger.info("Resolving reference dataset …")
            reference_path = existing_reference(args.reference)

            logger.info("Reference      : %s", reference_path)
            logger.info("Up genes       : %s", args.up)
            logger.info("Down genes     : %s", args.down)
            logger.info("Mode           : %s", args.mode)
            logger.info("Permutations   : %d", args.nperm)
            logger.info("Seed           : %d", args.seed)
            logger.info("Min/Max genes  : %d / %d", args.min_gene, args.max_gene)
            logger.info("Output dir     : %s", args.output)
            if args.leading_genes:
                logger.info("Leading genes for top %d drugs", args.leading_genes)

            run_pipeline(
                reference      = reference_path,
                up_file        = args.up,
                down_file      = args.down,
                seed           = args.seed,
                max_size       = args.max_gene,
                min_size       = args.min_gene,
                output         = args.output,
                mode           = args.mode,
                nperm          = args.nperm,
                leading_genes_n= args.leading_genes
            )
            success = True

        else:
            parser.print_help()
            success = True

    except FileNotFoundError as exc:
        logger.error("File not found: %s", exc)
        raise SystemExit(1)

    except Exception:
        logger.exception("Pipeline raised an unhandled exception:")
        raise SystemExit(1)

    finally:
        _log_session_footer(time.time() - start, success)


if __name__ == "__main__":
    main()
