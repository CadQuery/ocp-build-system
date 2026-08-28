set -e
set -o pipefail

# Locate the MSVC build tools. The toolset version (and potentially the VS year and
# edition) changes with every runner image update, so discover the directory instead
# of pinning it -- a stale hard-coded path just yields "dumpbin.exe: command not found".
MSVC_BIN=$(ls -d "/c/Program Files/Microsoft Visual Studio/"*/*/VC/Tools/MSVC/*/bin/Hostx64/x64 2>/dev/null | sort -V | tail -1)
if [ -z "$MSVC_BIN" ]; then
    echo "ERROR: could not locate the MSVC Hostx64/x64 tools directory" >&2
    ls -d "/c/Program Files/Microsoft Visual Studio/"*/*/VC/Tools/MSVC/* 2>/dev/null >&2 || true
    exit 1
fi
echo "Using MSVC tools from: $MSVC_BIN"
PATH="$MSVC_BIN":$PATH

for dll_file in ../bin/vtk*.dll; do
    echo "$dll_file :"
    def_file=$(basename "${dll_file%.*}.def")
    lib_file=$(basename "${dll_file%.*}.lib")
    dll_name=$(basename "$dll_file" .dll)

    echo "EXPORTS" > "$def_file"

    # Using Windows dumpbin command
    dumpbin.exe -exports "$dll_file" | awk 'NR>18 && $4 != "" {print $4}' >> "$def_file"

    # Using Windows lib command
    lib.exe /def:"$def_file" /out:"$lib_file" /machine:x64
done
