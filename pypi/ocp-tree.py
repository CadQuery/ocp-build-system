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

                    if obj.__name__ == "OCP.TopoDS":
                        f.write("# Compatibility with OCP 7.8.x\n")
                        f.write("TopoDS.Vertex_s = TopoDS.Vertex\n")
                        f.write("TopoDS.Edge_s = TopoDS.Edge\n")
                        f.write("TopoDS.Wire_s = TopoDS.Wire\n")
                        f.write("TopoDS.Face_s = TopoDS.Face\n")
                        f.write("TopoDS.Shell_s = TopoDS.Shell\n")
                        f.write("TopoDS.Solid_s = TopoDS.Solid\n")
                        f.write("TopoDS.Compound_s = TopoDS.Compound\n")
                        f.write("TopoDS.CompSolid_s = TopoDS.CompSolid\n")

                    if obj.__name__ == "OCP.TopoDS.TopoDS":
                        f.write("# Compatibility with OCP 7.8.x\n")
                        f.write("Vertex_s = Vertex\n")
                        f.write("Edge_s = Edge\n")
                        f.write("Wire_s = Wire\n")
                        f.write("Face_s = Face\n")
                        f.write("Shell_s = Shell\n")
                        f.write("Solid_s = Solid\n")
                        f.write("Compound_s = Compound\n")
                        f.write("CompSolid_s = CompSolid\n")

            traverse(obj, p2, depth + 1)


Path.mkdir(Path.cwd() / "OCP", exist_ok=True)
p = Path.cwd() / "OCP"
if platform.system() == "Windows" and has_vtk:
    shutil.copy("__init__win.py", Path.cwd() / "OCP" / "__init__.py")
else:
    shutil.copy("__init__.py", Path.cwd() / "OCP")
traverse(OCP, p)
