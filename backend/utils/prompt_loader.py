from pathlib import Path

import yaml


def load_prompt(path: Path, prompt_key: str) -> str:
    with open(path) as f:
        data = yaml.safe_load(f)
        return data[prompt_key]
