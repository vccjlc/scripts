#!/usr/bin/env python3
"""
Merge all PDFs in a folder into exactly N larger PDFs.

Usage:
    pip install pypdf
    python merge_into_n_pdfs.py /path/to/folder 10

The script writes merged_01.pdf … merged_N.pdf next to the source files.
"""

import argparse
import math
import os
from pathlib import Path
from typing import List

from pypdf import PdfMerger


def chunkify(items: List[Path], n_chunks: int) -> List[List[Path]]:
    """
    Split *items* into *n_chunks* lists whose sizes differ by at most one.

    Example: 15 items into 4 chunks → [4, 4, 4, 3]
    """
    if n_chunks <= 0:
        raise ValueError("n_chunks must be positive")

    n_chunks = min(n_chunks, len(items))  # never create empty chunks
    base_size = len(items) // n_chunks
    remainder = len(items) % n_chunks

    chunks, start = [], 0
    for i in range(n_chunks):
        extra = 1 if i < remainder else 0  # distribute the remainder
        end = start + base_size + extra
        chunks.append(items[start:end])
        start = end
    return chunks


def merge_pdfs(files: List[Path], output_path: Path) -> None:
    """Merge *files* into *output_path* using pypdf."""
    merger = PdfMerger()
    for pdf in files:
        merger.append(pdf)
    with output_path.open("wb") as fh:
        merger.write(fh)
    merger.close()


def main(folder: Path, n_outputs: int) -> None:
    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {folder}")
        return

    chunks = chunkify(pdf_files, n_outputs)

    for idx, group in enumerate(chunks, start=1):
        out_name = folder / f"merged_{idx:02d}.pdf"
        print(f"Merging {len(group)} files → {out_name.name}")
        merge_pdfs(group, out_name)

    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge all PDFs in a folder into N bigger PDFs."
    )
    parser.add_argument("folder", type=Path, help="Folder containing PDFs")
    parser.add_argument(
        "n", type=int, help="Number of merged PDF files to produce (N)"
    )
    args = parser.parse_args()

    if not args.folder.is_dir():
        parser.error(f"{args.folder} is not a directory")

    main(args.folder, args.n)
