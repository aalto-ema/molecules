from copy import deepcopy

import pytest

from molecules.chemistry.adapter import from_smiles, to_mol
from molecules.domain.document import Arrow, new_id
from molecules.mechanisms.steps import propose_next_step
from molecules.storage.native import load_document, save_document


def addition():
    d = from_smiles("[OH-].CC=O")
    donor, _, carbon, oxygen = d.atoms
    carbonyl = next(b for b in d.bonds if b.order == 2)
    d.arrows = [
        Arrow(new_id(), "electron", 0, 0, 20, 20, start_anchor=donor.id, end_anchor=carbon.id),
        Arrow(new_id(), "electron", 0, 0, 20, 20, start_anchor=carbonyl.id, end_anchor=oxygen.id),
    ]
    return d


def test_addition_duplicates_step_and_preserves_original(tmp_path):
    d = addition()
    before = deepcopy(d)
    proposal = propose_next_step(d)
    assert d == before
    next_atoms = [a for a in proposal.document.atoms if a.step == 1]
    assert [a.charge for a in next_atoms] == [0, 0, 0, -1]
    assert [a.identity for a in next_atoms] == [a.identity for a in d.atoms]
    assert len(proposal.document.atoms) == 8
    assert len(proposal.document.bonds) == 5
    to_mol(proposal.document)
    path = tmp_path / "mechanism.json"
    save_document(proposal.document, path)
    assert load_document(path) == proposal.document


def test_proton_transfer():
    d = from_smiles("[OH-].[H]Cl")
    oxygen = d.atoms[0]
    hydrogen = next(a for a in d.atoms if a.element == "H")
    chlorine = next(a for a in d.atoms if a.element == "Cl")
    bond = next(b for b in d.bonds if hydrogen.id in (b.start, b.end))
    d.arrows = [
        Arrow(new_id(), "electron", 0, 0, 1, 1, start_anchor=oxygen.id, end_anchor=hydrogen.id),
        Arrow(new_id(), "electron", 0, 0, 1, 1, start_anchor=bond.id, end_anchor=chlorine.id),
    ]
    proposal = propose_next_step(d)
    assert sorted(a.charge for a in proposal.document.atoms if a.step == 1) == [-1, 0, 0]


def test_unsupported_arrows_leave_source_untouched():
    d = addition()
    d.arrows[0] = Arrow(new_id(), "electron", 0, 0, 1, 1, electrons=1)
    before = deepcopy(d)
    with pytest.raises(ValueError):
        propose_next_step(d)
    assert d == before
