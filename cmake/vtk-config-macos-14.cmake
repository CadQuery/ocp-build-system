# vtk-config.cmake

# Set VTK version
set(VTK_MAJOR_VERSION 9)
set(VTK_MINOR_VERSION 2)
set(VTK_BUILD_VERSION 6)

# Set full VTK version
set(VTK_VERSION "${VTK_MAJOR_VERSION}.${VTK_MINOR_VERSION}.${VTK_BUILD_VERSION}")

# Set include and library directories
if(WIN32)
  set(HOME_DIR "$ENV{USERPROFILE}")
else()
  set(HOME_DIR "$ENV{HOME}")
endif()

set(VTK_INCLUDE_DIRS "${HOME_DIR}/opt/local/vtk-${VTK_VERSION}/include")
set(VTK_LIBRARY_DIRS "${HOME_DIR}/opt/local/vtk-${VTK_VERSION}/lib")

# Find Python interpreter and get version
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(PYTHON_VERSION "${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}")

# Define the components
set(VTK_MODULES_ENABLED
    WrappingTools
    WebPython
    WebCore
    Python
    vtksys
    WebGLExporter
    ViewsInfovis
    CommonColor
    ViewsContext2D
    loguru
    TestingRendering
    TestingCore
    RenderingQt
    PythonContext2D
    RenderingVolumeOpenGL2
    glew
    opengl
    RenderingMatplotlib
    PythonInterpreter
    RenderingLabel
    octree
    RenderingLOD
    RenderingLICOpenGL2
    RenderingImage
    RenderingContextOpenGL2
    IOXdmf2
    libxml2
    xdmf2
    hdf5
    IOVeraOut
    IOTecplotTable
    utf8
    IOSegY
    IOXdmf3
    xdmf3
    IOParallelXML
    IOPLY
    IOOggTheora
    theora
    ogg
    IONetCDF
    netcdf
    libproj
    IOMotionFX
    pegtl
    IOParallel
    jsoncpp
    IOMINC
    IOLSDyna
    IOInfovis
    zlib
    IOImport
    IOIOSS
    fmt
    ioss
    cgns
    exodusII
    IOFFMPEG
    IOVideo
    IOMovie
    IOExportPDF
    libharu
    IOExportGL2PS
    RenderingGL2PSOpenGL2
    gl2ps
    png
    IOExport
    RenderingVtkJS
    nlohmannjson
    RenderingSceneGraph
    IOExodus
    IOEnSight
    IOCityGML
    pugixml
    IOChemistry
    IOCesium3DTiles
    IOGeometry
    IOCONVERGECFD
    IOHDF
    IOCGNSReader
    IOAsynchronous
    IOAMR
    InteractionImage
    ImagingStencil
    ImagingStatistics
    ImagingMorphological
    ImagingMath
    ImagingFourier
    IOSQL
    sqlite
    GUISupportQt
    GeovisCore
    InfovisLayout
    ViewsCore
    InteractionWidgets
    RenderingVolume
    RenderingAnnotation
    ImagingHybrid
    ImagingColor
    InteractionStyle
    FiltersTopology
    FiltersSelection
    FiltersSMP
    FiltersPython
    FiltersProgrammable
    FiltersPoints
    FiltersVerdict
    verdict
    FiltersParallelImaging
    FiltersParallelDIY2
    FiltersImaging
    ImagingGeneral
    FiltersGeneric
    FiltersFlowPaths
    eigen
    FiltersAMR
    FiltersParallel
    FiltersTexture
    FiltersModeling
    DomainsChemistryOpenGL2
    RenderingOpenGL2
    RenderingHyperTreeGrid
    RenderingUI
    FiltersHyperTree
    FiltersHybrid
    DomainsChemistry
    CommonPython
    WrappingPythonCore
    ChartsCore
    InfovisCore
    FiltersExtraction
    ParallelDIY
    diy2
    IOXML
    IOXMLParser
    expat
    ParallelCore
    IOLegacy
    IOCore
    doubleconversion
    lz4
    lzma
    FiltersStatistics
    ImagingSources
    IOImage
    DICOMParser
    jpeg
    metaio
    tiff
    RenderingContext2D
    RenderingFreeType
    freetype
    kwiml
    RenderingCore
    FiltersSources
    ImagingCore
    FiltersGeometry
    FiltersGeneral
    CommonComputationalGeometry
    FiltersCore
    CommonExecutionModel
    CommonDataModel
    CommonSystem
    CommonMisc
    exprtk
    CommonTransforms
    CommonMath
    kissfft
    CommonCore
)

# Create imported targets for each module
foreach(module ${VTK_MODULES_ENABLED})
    if(NOT TARGET VTK::${module})
        add_library(VTK::${module} SHARED IMPORTED)
        if(${module} STREQUAL "WrappingPythonCore")
            set_target_properties(VTK::${module} PROPERTIES
                IMPORTED_LOCATION "${VTK_LIBRARY_DIRS}/libvtkWrappingPythonCore${PYTHON_VERSION}-${VTK_MAJOR_VERSION}.${VTK_MINOR_VERSION}.dylib"
                INTERFACE_INCLUDE_DIRECTORIES "${VTK_INCLUDE_DIRS}"
            )
        else()
            set_target_properties(VTK::${module} PROPERTIES
                IMPORTED_LOCATION "${VTK_LIBRARY_DIRS}/libvtk${module}-${VTK_MAJOR_VERSION}.${VTK_MINOR_VERSION}.dylib"
                INTERFACE_INCLUDE_DIRECTORIES "${VTK_INCLUDE_DIRS}"
            )
        endif()
    endif()
endforeach()

# Set VTK_LIBRARIES
set(VTK_LIBRARIES "")
foreach(module ${VTK_MODULES_ENABLED})
    list(APPEND VTK_LIBRARIES VTK::${module})
endforeach()

# Set VTK_FOUND
set(VTK_FOUND TRUE)

# Set VTK_USE_FILE (for backward compatibility)
set(VTK_USE_FILE "${CMAKE_CURRENT_LIST_DIR}/UseVTK.cmake")

# Print status
message(STATUS "Found VTK ${VTK_VERSION}")
message(STATUS "  Includes: ${VTK_INCLUDE_DIRS}")
message(STATUS "  Libraries: ${VTK_LIBRARIES}")
message(STATUS "  Python Version: ${Python3_VERSION}")
