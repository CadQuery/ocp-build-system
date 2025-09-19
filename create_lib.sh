find '/c/Program Files/Microsoft Visual Studio/2022/Enterprise' -iname dumpbin.exe
find '/c/Program Files/Microsoft Visual Studio/2022/Enterprise' -iname lib.exe
PATH='/c/Program Files/Microsoft Visual Studio/2022/Enterprise/VC/Tools/MSVC/14.42.34433/bin/Hostx64/x64/':$PATH
for dll_file in ../bin/vtk*.dll; do
    echo "$dll_file :"
    def_file=$(basename "${dll_file%.*}.def")
    lib_file=$(basename "${dll_file%.*}.lib")
    dll_name=$(basename "$dll_file" .dll)

    echo "EXPORTS" >> "$def_file"

    # Using Windows dumpbin command
    dumpbin.exe -exports "$dll_file" | awk 'NR>18 && $4 != "" {print $4}' >> "$def_file"

    # Using Windows lib command
    lib.exe /def:"$def_file" /out:"$lib_file" /machine:x64
done