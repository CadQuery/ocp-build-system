try:
    # Will only work on Windows
    def _vtkmodules():
        import os
        libs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'vtkmodules'))
        os.add_dll_directory(libs_dir)
    
    _vtkmodules()
except:
    pass
finally:
    del _vtkmodules

from OCP.OCP import *
from OCP.OCP import __version__