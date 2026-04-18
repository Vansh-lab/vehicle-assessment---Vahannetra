#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import urlretrieve

MODEL_URLS = {
    "sam2": "https://huggingface.co/facebook/sam2-hiera-large/resolve/main/model.safetensors",
    "yolov9": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov9c.pt",
    "efficientnet_b4": "https://download.pytorch.org/models/efficientnet_b4_rwightman-23ab8bcd.pth",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Download model weights into ml/weights")
    parser.add_argument("--model", choices=list(MODEL_URLS.keys()) + ["all"], default="all")
    parser.add_argument("--out-dir", default="ml/weights")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected = MODEL_URLS.keys() if args.model == "all" else [args.model]
    for key in selected:
        url = MODEL_URLS[key]
        suffix = ".pt" if "yolo" in key else ".pth" if "efficientnet" in key else ".safetensors"
        dest = out_dir / f"{key}{suffix}"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"skip: {dest} already exists")
            continue
        print(f"downloading {key} -> {dest}")
        urlretrieve(url, dest)
        print(f"saved: {dest}")


if __name__ == "__main__":
    main()
