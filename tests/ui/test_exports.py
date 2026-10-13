import xml.etree.ElementTree as ET

from PySide6.QtGui import QImage

from molecules.chemistry.adapter import from_smiles
from molecules.exports.visual import export


def test_transparent_and_colored_png(qapp, tmp_path):
    document = from_smiles("CC(=O)[O-]")
    transparent = tmp_path / "transparent.png"
    export(document, transparent, width=700, height=400)
    image = QImage(str(transparent))
    assert (image.width(), image.height()) == (700, 400)
    assert image.pixelColor(0, 0).alpha() == 0
    assert any(
        image.pixelColor(x, y).alpha() > 0 for x in range(100, 600, 5) for y in range(100, 300, 5)
    )
    colored = tmp_path / "colored.png"
    export(document, colored, background="#faeedd")
    assert QImage(str(colored)).pixelColor(0, 0).name() == "#faeedd"


def test_svg_and_pdf_contain_vector_drawing(qapp, tmp_path):
    document = from_smiles("N[C@@H](C)C(=O)O")
    svg, pdf = tmp_path / "drawing.svg", tmp_path / "drawing.pdf"
    export(document, svg, format="SVG")
    export(document, pdf, format="PDF")
    root = ET.parse(svg).getroot()
    assert root.tag.endswith("svg")
    assert not any(e.tag.endswith("image") for e in root.iter())
    assert pdf.read_bytes().startswith(b"%PDF")
    assert pdf.stat().st_size > 1000


def test_long_terminal_labels_do_not_have_bonds_drawn_through_them(qapp):
    from dataclasses import replace

    from PySide6.QtWidgets import QGraphicsLineItem

    from molecules.rendering.scene import content_scene

    document = from_smiles("CO")
    atom = document.atoms[-1]
    document.atoms[-1] = replace(atom, label="CH2CH2OCH2CH2OH")
    scene = content_scene(document)
    label = next(i for i in scene.items() if i.data(0) == "atom" and i.data(1) == atom.id)
    rect = label.sceneBoundingRect()
    bonds = [i for i in scene.items() if isinstance(i, QGraphicsLineItem)]
    assert bonds
    assert all(not line.sceneBoundingRect().intersects(rect) for line in bonds)


def test_failed_vector_export_preserves_destination_and_cleans_up(qapp, tmp_path, monkeypatch):
    import pytest

    from molecules.exports import visual

    document = from_smiles("CCO")

    def fail(*args, **kwargs):
        raise RuntimeError("Rendering failed")

    monkeypatch.setattr(visual, "paint", fail)
    for format in ("SVG", "PDF"):
        path = tmp_path / ("existing." + format.lower())
        path.write_bytes(b"Previous export")
        with pytest.raises(RuntimeError, match="Rendering failed"):
            export(document, path, format=format)
        assert path.read_bytes() == b"Previous export"
    assert {p.name for p in tmp_path.iterdir()} == {"existing.svg", "existing.pdf"}
