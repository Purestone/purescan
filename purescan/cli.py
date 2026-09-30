"""Command-line interface for PureScan."""

import argparse
from pathlib import Path
import sys
import time
from typing import List

from . import __version__
from .pdf_processor import clean_pdf


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="purescan",
        description="PureScan: Lossless multi-page watermark inversion for scanned PDFs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  purescan document.pdf -o cleaned.pdf
  purescan document.pdf --in-place
  purescan ./scans_folder/ -o ./cleaned_folder/
        """,
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input PDF file or directory of PDF files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PDF path or destination directory (required if not using --in-place).",
    )
    parser.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        help="Modify files in place (creates a .bak backup file).",
    )
    parser.add_argument(
        "-s",
        "--sample-pages",
        type=int,
        default=25,
        help="Number of pages to sample for watermark detection and template extraction (default: 25).",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress outputs.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def process_single_file(
    src_file: Path,
    dest_file: Path | None,
    in_place: bool,
    sample_pages: int,
    quiet: bool,
) -> bool:
    if not quiet:
        print(f"\n📄 Processing: {src_file.name}")

    start_time = time.time()
    pbar = None

    if not quiet:
        try:
            from tqdm import tqdm
            pbar = tqdm(total=100, unit="page", desc="  Inverting", leave=False)
        except ImportError:
            pbar = None

    def on_progress(cur: int, total: int) -> None:
        if pbar:
            pbar.total = total
            pbar.n = cur
            pbar.refresh()

    try:
        res = clean_pdf(
            src_file,
            output_path=dest_file,
            in_place=in_place,
            sample_count=sample_pages,
            progress_callback=on_progress if not quiet else None,
        )
    except Exception as e:
        if pbar:
            pbar.close()
        print(f"❌ Error: {e}", file=sys.stderr)
        return False

    if pbar:
        pbar.close()

    elapsed = time.time() - start_time
    if res.get("success"):
        cleaned = res["pages_cleaned"]
        total = res["pages_total"]
        out_path = res["output_path"]
        print(f"✅ Finished in {elapsed:.2f}s: cleaned {cleaned}/{total} pages -> {out_path}")
        return True
    else:
        msg = res.get("message", "Skipped")
        print(f"⚠️  {msg}")
        return False


def main(argv: List[str] | None = None) -> int:
    parser = get_parser()
    args = parser.parse_args(argv)

    src_path: Path = args.input.resolve()
    if not src_path.exists():
        print(f"Error: path not found: {src_path}", file=sys.stderr)
        return 1

    if not args.in_place and args.output is None:
        print("Error: must provide -o/--output or specify -i/--in-place.", file=sys.stderr)
        return 1

    if src_path.is_file():
        if src_path.suffix.lower() != ".pdf":
            print(f"Error: {src_path.name} is not a PDF file.", file=sys.stderr)
            return 1
        dest = args.output.resolve() if args.output else None
        success = process_single_file(
            src_path,
            dest,
            in_place=args.in_place,
            sample_pages=args.sample_pages,
            quiet=args.quiet,
        )
        return 0 if success else 1

    elif src_path.is_dir():
        pdf_files = sorted(list(src_path.glob("*.pdf")))
        if not pdf_files:
            print(f"No PDF files found in {src_path}", file=sys.stderr)
            return 0

        out_dir: Path | None = None
        if not args.in_place and args.output:
            out_dir = args.output.resolve()
            out_dir.mkdir(parents=True, exist_ok=True)

        success_count = 0
        for pdf_file in pdf_files:
            if pdf_file.name.endswith(".bak.pdf") or pdf_file.name.endswith(".pdf.bak"):
                continue
            dest_file = (out_dir / pdf_file.name) if out_dir else None
            ok = process_single_file(
                pdf_file,
                dest_file,
                in_place=args.in_place,
                sample_pages=args.sample_pages,
                quiet=args.quiet,
            )
            if ok:
                success_count += 1

        print(f"\n🎉 Batch complete: {success_count}/{len(pdf_files)} PDFs processed successfully.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
