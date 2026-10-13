import math
from copy import deepcopy

import pytest

from molecules.domain.document import Atom, Bond, Document
from molecules.domain.geometry import rotate_molecules
from molecules.domain.pathways import add_product, connect_molecules
from molecules.storage.native import load_document, save_document


def reactant():
    return Document(
        atoms=[Atom("a1", "C", 0, 0), Atom("a2", "O", 60, 0, -1)], bonds=[Bond("b1", "a1", "a2")]
    )


def product():
    return Document(
        atoms=[Atom("p1", "C", 0, 0), Atom("p2", "O", 60, 0)], bonds=[Bond("pb", "p1", "p2", 2)]
    )


@pytest.mark.parametrize("direction", ["right", "down", "left", "up"])
def test_add_product_is_explicit_and_respects_direction(direction, tmp_path):
    d = reactant()
    before = deepcopy(d)
    result = add_product(d, {"a1"}, product(), direction, "2H⁺ + 2e⁻")
    assert d == before
    assert len(result.arrows) == 1
    arrow = result.arrows[0]
    assert arrow.kind == "reaction"
    assert arrow.label == "2H⁺ + 2e⁻"
    assert set(arrow.start_group) == {"a1", "a2"}
    assert set(arrow.end_group) == {"p1", "p2"}
    new = next(a for a in result.atoms if a.id == "p1")
    assert {"right": new.x > 60, "left": new.x < 0, "down": new.y > 0, "up": new.y < 0}[direction]
    path = tmp_path / "path.json"
    save_document(result, path)
    assert load_document(path) == result


def test_same_molecule_cannot_be_linked_to_itself():
    with pytest.raises(ValueError):
        connect_molecules(reactant(), {"a1"}, {"a2"})


def test_rigid_rotation_preserves_graph_and_pair_distances():
    d = reactant()
    before = deepcopy(d)
    result = rotate_molecules(d, {"a1"}, 90)
    assert d == before
    assert result.bonds == before.bonds
    a, b = result.atoms
    assert math.hypot(b.x - a.x, b.y - a.y) == pytest.approx(60)
    assert a.x == pytest.approx(b.x)
    assert b.charge == -1
    assert rotate_molecules(d, {"a1"}, 360) == d


def test_nonfinite_rotation_rejected():
    with pytest.raises(ValueError):
        rotate_molecules(reactant(), {"a1"}, float("nan"))


def test_v3_arrows_migrate_with_empty_pathway_fields():
    import json
    from dataclasses import asdict

    from molecules.domain.document import Arrow
    from molecules.storage.native import decode_document

    d = reactant()
    d.arrows = [Arrow("arrow", "reaction", 100, 0, 200, 0)]
    data = asdict(d)
    data["schema_version"] = 3
    for a in data["arrows"]:
        for name in ("label", "label_side", "label_offset", "start_group", "end_group"):
            del a[name]
    restored = decode_document(json.dumps(data).encode())
    assert restored == d
