import inspect
import os
import platform
import shutil
import sys
from pathlib import Path

sys.path.append(".")

has_vtk = False
if platform.system() == "Windows":
    if len(sys.argv) >= 2:
        occt = sys.argv[1]
        os.add_dll_directory(
            Path(os.path.expanduser("~"))
            / "opt"
            / "local"
            / occt
            / "win64"
            / "vc14"
            / "bin"
        )
    if len(sys.argv) == 3:
        vtk = sys.argv[2]
        os.add_dll_directory(
            Path(os.path.expanduser("~")) / "opt" / "local" / vtk / "bin"
        )
        has_vtk = True


import OCP


def traverse(module, p, depth=0):
    prefix = "  " * depth
    print(f"{prefix}{module.__name__}")

    for name, obj in inspect.getmembers(module):
        if inspect.ismodule(obj) and obj.__name__.startswith(module.__name__):
            Path.mkdir(p / name, exist_ok=True)
            p2 = Path(p / name)
            if name.startswith("IVtk"):
                with open(p2 / "__init__.py", "w") as f:
                    f.write("try:\n")
                    f.write("  import vtk\n")
                    f.write(f"  from ..{obj.__name__} import *\n")
                    f.write("except:\n")
                    f.write("  print('VTK not installed')\n")
            else:
                with open(p2 / "__init__.py", "w") as f:
                    f.write(f"from ..{obj.__name__} import *\n")
            traverse(obj, p2, depth + 1)


Path.mkdir(Path.cwd() / "OCP", exist_ok=True)
p = Path.cwd() / "OCP"
if platform.system() == "Windows" and has_vtk:
    shutil.copy("__init__win.py", Path.cwd() / "OCP" / "__init__.py")
else:
    shutil.copy("__init__.py", Path.cwd() / "OCP")
traverse(OCP, p)
