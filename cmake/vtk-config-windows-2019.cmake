# vtk-config.cmake

# Set VTK version
set(VTK_MAJOR_VERSION 9)
set(VTK_MINOR_VERSION 3)
set(VTK_BUILD_VERSION 1)

# Set full VTK version
set(VTK_VERSION "${VTK_MAJOR_VERSION}.${VTK_MINOR_VERSION}.${VTK_BUILD_VERSION}")

# Set include and library directories
if(WIN32)
  set(HOME_DIR "$ENV{USERPROFILE}")
else()
  set(HOME_DIR "$ENV{HOME}")
endif()

set(VTK_INCLUDE_DIRS "${HOME_DIR}/opt/local/vtk-${VTK_VERSION}/include/vtk-${VTK_MAJOR_VERSION}.${VTK_MINOR_VERSION}")
set(VTK_LIBRARY_DIRS "${HOME_DIR}/opt/local/vtk-${VTK_VERSION}/lib")
set(VTK_DLL_DIRS "${HOME_DIR}/opt/local/vtk-${VTK_VERSION}/bin")

set(VTK_INCLUDE_DIR "${HOME_DIR}/opt/local/vtk-${VTK_VERSION}/include/vtk-${VTK_MAJOR_VERSION}.${VTK_MINOR_VERSION}")
set(VTK_LIBRARY_DIR "${HOME_DIR}/opt/local/vtk-${VTK_VERSION}/lib")
set(VTK_DLL_DIR "${HOME_DIR}/opt/local/vtk-${VTK_VERSION}/bin")

# Find Python interpreter and get version
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(PYTHON_VERSION "${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}")

set(SUFFIX "-${VTK_MAJOR_VERSION}.${VTK_MINOR_VERSION}")

# Define the components
set(VTK_MODULES_ENABLED
    AcceleratorsVTKmCore
    AcceleratorsVTKmDataModel
    AcceleratorsVTKmFilters
    cgns
    ChartsCore
    CommonColor
    CommonComputationalGeometry
    CommonCore
    CommonDataModel
    CommonExecutionModel
    CommonMath
    CommonMisc
    CommonPython
    CommonSystem
    CommonTransforms
    DICOMParser
    DomainsChemistry
    DomainsChemistryOpenGL2
    doubleconversion
    exodusII
    expat
    FiltersAMR
    FiltersCellGrid
    FiltersCore
    FiltersExtraction
    FiltersFlowPaths
    FiltersGeneral
    FiltersGeneric
    FiltersGeometry
    FiltersGeometryPreview
    FiltersHybrid
    FiltersHyperTree
    FiltersImaging
    FiltersModeling
    FiltersParallel
    FiltersParallelDIY2
    FiltersParallelImaging
    FiltersParallelStatistics
    FiltersPoints
    FiltersProgrammable
    FiltersPython
    FiltersReduction
    FiltersSelection
    FiltersSMP
    FiltersSources
    FiltersStatistics
    FiltersTensor
    FiltersTexture
    FiltersTopology
    FiltersVerdict
    fmt
    freetype
    GeovisCore
    gl2ps
    glew
    h5part
    hdf5_hl
    hdf5
    ImagingColor
    ImagingCore
    ImagingFourier
    ImagingGeneral
    ImagingHybrid
    ImagingMath
    ImagingMorphological
    ImagingOpenGL2
    ImagingSources
    ImagingStatistics
    ImagingStencil
    InfovisCore
    InfovisLayout
    InteractionImage
    InteractionStyle
    InteractionWidgets
    IOAMR
    IOAsynchronous
    IOCellGrid
    IOCesium3DTiles
    IOCGNSReader
    IOChemistry
    IOCityGML
    IOCONVERGECFD
    IOCore
    IOEnSight
    IOExodus
    IOExport
    IOExportGL2PS
    IOExportPDF
    IOFLUENTCFF
    IOGeoJSON
    IOGeometry
    IOH5part
    IOH5Rage
    IOHDF
    IOImage
    IOImport
    IOInfovis
    IOIOSS
    IOLegacy
    IOLSDyna
    IOMINC
    IOMotionFX
    IOMovie
    IONetCDF
    IOOggTheora
    IOOMF
    IOParallel
    IOParallelExodus
    IOParallelLSDyna
    IOParallelXML
    IOPIO
    IOPLY
    IOSegY
    IOSQL
    ioss
    IOTecplotTable
    IOTRUCHAS
    IOVeraOut
    IOVideo
    IOVPIC
    IOXdmf2
    IOXML
    IOXMLParser
    jpeg
    jsoncpp
    kissfft
    libharu
    libproj
    libxml2
    loguru
    lz4
    lzma
    m_cont
    m_filter_clean_grid
    m_filter_connected_components
    m_filter_contour
    m_filter_core
    m_filter_density_estimate
    m_filter_entity_extraction
    m_filter_field_conversion
    m_filter_field_transform
    m_filter_geometry_refinement
    m_filter_mesh_info
    m_filter_resampling
    m_filter_vector_analysis
    m_worklet
    mdiympi_nompi
    metaio
    netcdf
    ogg
    ParallelCore
    ParallelDIY
    png
    pugixml
    PythonContext2D
    PythonInterpreter
    RenderingAnnotation
    RenderingCellGrid
    RenderingContext2D
    RenderingContextOpenGL2
    RenderingCore
    RenderingExternal
    RenderingFreeType
    RenderingGL2PSOpenGL2
    RenderingHyperTreeGrid
    RenderingImage
    RenderingLabel
    RenderingLICOpenGL2
    RenderingLOD
    RenderingMatplotlib
    RenderingOpenGL2
    RenderingParallel
    RenderingSceneGraph
    RenderingUI
    RenderingVolume
    RenderingVolumeAMR
    RenderingVolumeOpenGL2
    RenderingVR
    RenderingVtkJS
    sqlite
    sys
    TestingRendering
    theora
    tiff
    verdict
    ViewsContext2D
    ViewsCore
    ViewsInfovis
    vpic
    WebCore
    WebGLExporter
    WrappingPythonCore
    xdmf2
    zlib
)

# Create imported targets for each module
foreach(module ${VTK_MODULES_ENABLED})
    if(NOT TARGET VTK::${module})
        add_library(VTK::${module} SHARED IMPORTED)
        if(${module} STREQUAL "WrappingPythonCore")
            file(GLOB VTK_DLL "${VTK_DLL_DIRS}/vtk${module}${PYTHON_VERSION}${SUFFIX}*.dll")
            file(GLOB VTK_LIB "${VTK_LIBRARY_DIRS}/vtk${module}${PYTHON_VERSION}${SUFFIX}*.lib")        
        else()
            file(GLOB VTK_DLL "${VTK_DLL_DIRS}/vtk${module}${SUFFIX}*.dll")
            file(GLOB VTK_LIB "${VTK_LIBRARY_DIRS}/vtk${module}${SUFFIX}*.lib")        
        endif()
        message(STATUS "VTK::${module} DLL: ${VTK_DLL}   LIB: ${VTK_LIB}")
        set_target_properties(VTK::${module} PROPERTIES
            IMPORTED_LOCATION "${VTK_DLL}"
            IMPORTED_IMPLIB "${VTK_LIB}"
            INTERFACE_INCLUDE_DIRECTORIES "${VTK_INCLUDE_DIRS}"
        )
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
message(STATUS "  Libraries: ${VTK_LIBRARY_DIRS}")
message(STATUS "  DLLs: ${VTK_DLL_DIRS}")
message(STATUS "  DLLs: ${VTK_LIBRARIES}")
message(STATUS "  Python Version: ${Python3_VERSION}")
