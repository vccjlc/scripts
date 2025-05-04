#!/usr/bin/env python3
"""
Merge all PDFs in a folder into exactly N larger PDFs.
Outputs go to a sub‑folder (default: merged_pdfs).

remember to
pip install pypdf

Examples
--------
python merge_into_n_pdfs.py 10               # current dir → ./merged_pdfs
python merge_into_n_pdfs.py 7 ./invoices     # explicit input dir
python merge_into_n_pdfs.py 5 . --out big    # custom output sub‑folder
"""

import argparse
from pathlib import Path
from typing import List

from pypdf import PdfReader, PdfWriter


# ---------- helpers ----------------------------------------------------------
def chunkify(items: List[Path], n_chunks: int) -> List[List[Path]]:
    n_chunks = max(1, min(n_chunks, len(items)))
    base, rem = divmod(len(items), n_chunks)

    chunks, start = [], 0
    for i in range(n_chunks):
        end = start + base + (1 if i < rem else 0)
        chunks.append(items[start:end])
        start = end
    return chunks


def merge_pdfs(files: List[Path], output_path: Path) -> None:
    writer = PdfWriter()
    for pdf in files:
        reader = PdfReader(pdf)
        for page in reader.pages:
            writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as fh:
        writer.write(fh)


# ---------- main -------------------------------------------------------------
def main(folder: Path, n_outputs: int, out_subdir: str) -> None:
    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {folder}")
        return

    out_dir = folder / out_subdir
    chunks = chunkify(pdf_files, n_outputs)

    for idx, group in enumerate(chunks, 1):
        out_name = out_dir / f"merged_{idx:02d}.pdf"
        print(f"Merging {len(group):>3} files → {out_name.relative_to(folder)}")
        merge_pdfs(group, out_name)

    print(f"\nDone. {len(chunks)} merged PDFs written to {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge all PDFs in a folder into N larger PDFs."
    )
    parser.add_argument("n", type=int, help="Number of merged PDFs to create")
    parser.add_argument(
        "folder",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="Folder with PDFs (defaults to current directory)",
    )
    parser.add_argument(
        "--out", "-o", default="merged_pdfs",
        help="Sub‑folder for outputs (default: merged_pdfs)",
    )
    args = parser.parse_args()

    if not args.folder.is_dir():
        parser.error(f"{args.folder} is not a directory")

    main(args.folder.resolve(), args.n, args.out)
