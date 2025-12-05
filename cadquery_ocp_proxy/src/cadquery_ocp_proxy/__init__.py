from cadquery_ocp_proxy._version import __version__

try:
    from OCP.IVtkOCC import IVtkOCC_Shape

    print("VTK installed")
except ImportError:
    print("VTK not installed")
