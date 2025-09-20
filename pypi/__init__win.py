def _vtkmodules():
    import os
    # import sys

    # if sys.version_info[0] == 3 and sys.version_info[1] == 13:
    #     libs_dir = os.path.abspath(
    #         os.path.join(os.path.dirname(__file__), os.pardir, "cadquery_vtk.libs")
    #     )
    # else:
    #     libs_dir = os.path.abspath(
    #         os.path.join(os.path.dirname(__file__), os.pardir, "vtk.libs")
    #     )

    libs_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "vtk.libs")
    )
    os.add_dll_directory(libs_dir)


_vtkmodules()
del _vtkmodules

from OCP.OCP import *

from OCP.OCP import __version__
