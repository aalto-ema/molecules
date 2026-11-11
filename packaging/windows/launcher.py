"""Entry point for the standalone Windows executable."""

import sys
import traceback
from pathlib import Path

from molecules.app import main


def smoke_test(output: Path) -> int:
    """Exercise native dependencies and bundled assets in the installed app."""
    output.mkdir(parents=True, exist_ok=True)
    report = output / "smoke-test.txt"
    try:
        from PySide6.QtWidgets import QApplication

        from molecules.chemistry.adapter import from_smiles
        from molecules.exports.visual import export
        from molecules.storage.native import load_document, save_document
        from molecules.ui import theme
        from molecules.ui.window import MainWindow

        app = QApplication([sys.argv[0]])
        window = MainWindow()
        window.show()
        app.processEvents()
        asset = Path(theme.__file__).parent / "assets" / "chevron.svg"
        if not window.isVisible() or not asset.is_file():
            raise RuntimeError("The installed window or its dropdown asset is missing.")

        document = from_smiles("CCO")
        drawing = output / "ethanol.molecules.json"
        save_document(document, drawing)
        if len(document.atoms) != 3 or load_document(drawing) != document:
            raise RuntimeError("The installed app could not round-trip an ethanol drawing.")
        for kind, signature in (("PNG", b"\x89PNG"), ("SVG", b"<?xml"), ("PDF", b"%PDF")):
            path = output / f"ethanol.{kind.lower()}"
            export(document, path, format=kind, width=320, height=240)
            if not path.read_bytes().startswith(signature):
                raise RuntimeError(f"The installed app produced an invalid {kind} export.")
        window.close()
    except Exception:
        report.write_text(traceback.format_exc(), encoding="utf-8")
        return 1
    report.write_text("Installed app smoke test passed.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        raise SystemExit(smoke_test(Path(sys.argv[2])))
    raise SystemExit(main())
