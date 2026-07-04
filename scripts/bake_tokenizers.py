#!/usr/bin/env python3
"""Bake tokenizers into the image at build time.

Downloads HF tokenizers into TOKENIZER_BUNDLED_PATH so a closed site resolves
them offline. Layout matches TokenizerManager: <bundled>/<org--name>.

Fail-soft: failures are logged and skipped, and an empty result does not break
the build (the runtime falls back) unless BAKE_REQUIRED=1. SKIP_BAKE=1 skips,
HF_TOKEN authenticates gated repos, BAKE_TOKENIZERS overrides the list.
"""
import os
import sys

# Classic HTTP download path, bounded metadata calls (no xet CDN).
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "15")

DEFAULT_TOKENIZERS = [
    "mistralai/Mistral-7B-Instruct-v0.3",       # also the Mistral Medium proxy
    "mistralai/Mistral-Small-24B-Instruct-2501",
    "mistralai/Mistral-Nemo-Instruct-2407",
]


def main() -> int:
    if os.getenv("SKIP_BAKE"):
        print("[bake] SKIP_BAKE set, skipping", flush=True)
        return 0

    from transformers import AutoTokenizer

    bundled_path = os.getenv("TOKENIZER_BUNDLED_PATH", "/opt/linto/tokenizers")
    raw = os.getenv("BAKE_TOKENIZERS", "").strip()
    repos = [r.strip() for r in raw.split(",") if r.strip()] if raw else DEFAULT_TOKENIZERS
    token = os.getenv("HF_TOKEN") or None

    os.makedirs(bundled_path, exist_ok=True)
    ok, failed = [], []
    for repo in repos:
        dest = os.path.join(bundled_path, repo.replace("/", "--"))
        try:
            print(f"[bake] downloading {repo}", flush=True)
            tok = AutoTokenizer.from_pretrained(repo, token=token)
            tok.save_pretrained(dest)
            ok.append(repo)
            print(f"[bake] OK    {repo} -> {dest}", flush=True)
        except Exception as e:  # skip this repo, keep going
            failed.append(repo)
            print(f"[bake] FAIL  {repo}: {e}", file=sys.stderr, flush=True)

    print(f"[bake] baked {len(ok)}/{len(repos)}: ok={ok} failed={failed}", flush=True)
    if not ok:
        msg = "[bake] nothing baked"
        if os.getenv("BAKE_REQUIRED"):
            print(f"{msg}, BAKE_REQUIRED set -> failing the build", file=sys.stderr, flush=True)
            return 1
        print(f"{msg} (runtime will resolve offline/bounded); continuing", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
