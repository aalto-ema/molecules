"""Keep RDKit resources and Windows DLLs alongside their extension modules."""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_delvewheel_libs_directory,
    collect_dynamic_libs,
)

datas, binaries = collect_delvewheel_libs_directory(
    "rdkit", datas=collect_data_files("rdkit"), binaries=collect_dynamic_libs("rdkit")
)
