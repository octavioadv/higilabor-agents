import importlib.util
import json
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

def import_script_module(relative_path: str, prefix: str):
    module_name = f"{prefix}_{uuid.uuid4().hex}"
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def make_temp_task(tmp_path: Path, base_task_name: str, mutate_fn=None) -> Path:
    source = REPO_ROOT / "tasks" / base_task_name
    data = load_json(source)
    if mutate_fn is not None:
        mutated = mutate_fn(data)
        if mutated is not None:
            data = mutated
    target = tmp_path / base_task_name
    write_json(target, data)
    return target

def snapshot_paths(pattern: str) -> set[Path]:
    return set(REPO_ROOT.glob(pattern))

def new_paths(before: set[Path], pattern: str) -> list[Path]:
    after = set(REPO_ROOT.glob(pattern))
    return sorted(after - before)
