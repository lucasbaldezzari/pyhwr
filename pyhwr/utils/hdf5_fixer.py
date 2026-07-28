import re
import os
from pathlib import Path


_CORRUPTED_HDF5 = re.compile(
    r"^(.+\.hdf5)\d{4}\.\d{2}\.\d{2}_\d{2}\.\d{2}\.\d{2}\.hdf5$"
)


def fix_hdf5_filenames(folder, recursive=False, dry_run=False):
    """
    Renombra archivos HDF5 cuyo nombre tiene una fecha/hora duplicada al final.

    El problema: gtec guarda archivos con el nombre correcto seguido de la fecha
    y una segunda extensión .hdf5, por ejemplo:
        sub-01_ses-02_task-eog_run-03_eeg.hdf52026.06.09_10.20.36.hdf5
    Este función los renombra a su forma correcta:
        sub-01_ses-02_task-eog_run-03_eeg.hdf5

    Si el nombre destino ya existe, el archivo no se renombra y se reporta el conflicto.

    Parámetros
    ----------
    folder : str | Path
        Carpeta raíz donde buscar archivos.
    recursive : bool
        Si True, busca también en subcarpetas.
    dry_run : bool
        Si True, solo imprime lo que haría sin renombrar nada.

    Retorna
    -------
    list[dict]
        Lista de resultados con claves 'original', 'target', 'status'.
        'status' puede ser 'renamed', 'skipped_conflict', 'dry_run'.
    """
    folder = Path(folder)
    pattern = "**/*.hdf5" if recursive else "*.hdf5"
    results = []

    for path in folder.glob(pattern):
        match = _CORRUPTED_HDF5.match(path.name)
        if not match:
            continue

        correct_name = match.group(1)
        target = path.parent / correct_name

        entry = {"original": path, "target": target}

        if dry_run:
            entry["status"] = "dry_run"
            print(f"[dry-run] {path.name}  ->  {correct_name}")
        elif target.exists():
            entry["status"] = "skipped_conflict"
            print(f"[conflict] '{correct_name}' ya existe, se omite: {path.name}")
        else:
            path.rename(target)
            entry["status"] = "renamed"
            print(f"[ok] {path.name}  ->  {correct_name}")

        results.append(entry)

    if not results:
        print(f"No se encontraron archivos con el problema en: {folder}")

    return results


if __name__ == "__main__":
    fix_hdf5_filenames("D:\\dataset\\DataBase\\sub-06\\ses-01")
    pass