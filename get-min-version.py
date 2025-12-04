from pathlib import Path
from packaging.requirements import Requirement
from packaging.version import Version
import sys

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # pip install tomli

def get_dependency_min_version(name: str, pyproject_path: str = "pyproject.toml"):
    with open(pyproject_path, "rb") as f:
       data = tomllib.load(f)

    deps = data["project"]["dependencies"]
    for dep in deps:
        req = Requirement(dep)
        if req.name == name:
            ge_versions = [
               s.version for s in req.specifier if s.operator == ">="
            ]
            v = ge_versions[0]
            if len(v.split(".")) == 2:
                return f"{v}.0"
            else:
                return v

proj_toml = sys.argv[1]
lib = sys.argv[2]
print(get_dependency_min_version(lib, proj_toml))