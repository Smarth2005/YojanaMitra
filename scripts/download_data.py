"""Download the source scheme PDFs from Hugging Face."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import snapshot_download


DATASET_ID = "shrijayan/gov_myscheme"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/raw"))
    parser.add_argument("--repo-id", default=os.getenv("HF_DATASET_ID", DATASET_ID))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    path = snapshot_download(
        repo_id=args.repo_id,
        repo_type="dataset",
        local_dir=str(args.output),
        local_dir_use_symlinks=False,
    )
    print(f"Downloaded {args.repo_id} to {path}")


if __name__ == "__main__":
    main()
