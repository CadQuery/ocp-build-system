def _vtkmodules():
    import os
    libs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'vtk.libs'))
    os.add_dll_directory(libs_dir)

_vtkmodules()
del _vtkmodules

from OCP.OCP import *
from OCP.OCP import __version__