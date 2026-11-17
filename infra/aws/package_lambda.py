import zipfile
from pathlib import Path

root = Path("/lambda")
target = Path("/artifacts/function.zip")
target.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc"):
            archive.write(path, path.relative_to(root))
print("Packaged Lambda artifact")
