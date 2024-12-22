PATH='/c/Program Files (x86)/Microsoft Visual Studio 14.0/VC/bin/':$PATH

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