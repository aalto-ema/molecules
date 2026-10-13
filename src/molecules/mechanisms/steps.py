"""Propose simple pair-electron transformations without predicting chemistry."""

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, replace

from molecules.domain.document import Arrow, Bond, Document, Note, new_id


@dataclass
class StepProposal:
    document: Document
    changes: list[str]
    step: int
    atom_ids: set[str]
    source_step: int = 0


def propose_next_step(document: Document, arrow_ids: set[str] | None = None) -> StepProposal:
    document.validate()
    atoms = {a.id: a for a in document.atoms}
    bonds = {b.id: b for b in document.bonds}
    latest = max((a.step for a in document.atoms), default=0)

    def anchor_atoms(identity):
        if identity in atoms:
            return {identity}
        if identity in bonds:
            return {bonds[identity].start, bonds[identity].end}
        return set()

    arrows = [
        a
        for a in document.arrows
        if a.kind == "electron"
        and (
            (a.id in arrow_ids)
            if arrow_ids
            else not a.start_anchor
            or any(atoms[i].step == latest for i in anchor_atoms(a.start_anchor))
        )
    ]
    if not arrows:
        raise ValueError("Draw electron-flow arrows on the current step, or select arrows to use.")
    selected_atoms = set()
    charge_delta = defaultdict(int)
    lone_pair_delta = defaultdict(int)
    bond_delta = defaultdict(int)
    changes = []
    for arrow in arrows:
        if arrow.electrons != 2:
            raise ValueError(
                "Next-step assistance currently supports electron pairs. "
                "Fishhook arrows remain editable drawings."
            )
        start, end = arrow.start_anchor, arrow.end_anchor
        if not start or not end:
            raise ValueError("Next-step arrows must be attached to atoms or bonds at both ends.")
        involved = anchor_atoms(start) | anchor_atoms(end)
        if len({atoms[i].step for i in involved}) != 1:
            raise ValueError("Each electron arrow must stay within one mechanism step.")
        selected_atoms.update(involved)
        if start in atoms and end in atoms and start != end:
            connection = frozenset((start, end))
            existing = next(
                (b for b in bonds.values() if {b.start, b.end} == set(connection)), None
            )
            if existing and existing.aromatic:
                raise ValueError(
                    "Aromatic transformations need manual editing; "
                    "the assistant will not guess a resonance form."
                )
            bond_delta[connection] += 1
            lone_pair_delta[start] -= 1
            charge_delta[start] += 1
            charge_delta[end] -= 1
            changes.append(
                f"Form/increase {atoms[start].element}–{atoms[end].element} bond; "
                "transfer an electron pair."
            )
        elif start in bonds and end in (bonds[start].start, bonds[start].end):
            bond = bonds[start]
            if bond.aromatic:
                raise ValueError("Aromatic cleavage needs manual editing.")
            other = bond.end if end == bond.start else bond.start
            bond_delta[frozenset((bond.start, bond.end))] -= 1
            lone_pair_delta[end] += 1
            charge_delta[other] += 1
            charge_delta[end] -= 1
            changes.append(
                f"Reduce/break {atoms[bond.start].element}–{atoms[bond.end].element} bond; "
                f"pair goes to {atoms[end].element}."
            )
        else:
            raise ValueError(
                "Supported flows are atom → atom formation and bond → one endpoint cleavage. "
                "Move the arrow target to a specific atom, or edit the next drawing manually."
            )
    if len({atoms[i].step for i in selected_atoms}) != 1:
        raise ValueError("Create one mechanism step at a time; select arrows from the same step.")
    # Include the complete connected reactants, including the disconnected donor.
    changed = True
    while changed:
        before = len(selected_atoms)
        for bond in bonds.values():
            if bond.start in selected_atoms or bond.end in selected_atoms:
                selected_atoms.update((bond.start, bond.end))
        changed = len(selected_atoms) != before
    result = deepcopy(document)
    step = max((a.step for a in document.atoms), default=0) + 1
    identities = {i: new_id() for i in selected_atoms}
    left = min(atoms[i].x for i in selected_atoms)
    right = max(a.x for a in document.atoms)
    offset = right - left + 230
    for old in document.atoms:
        if old.id in selected_atoms:
            result.atoms.append(
                replace(
                    old,
                    id=identities[old.id],
                    identity=old.identity or old.id,
                    x=old.x + offset,
                    charge=old.charge + charge_delta[old.id],
                    lone_pairs=max(0, old.lone_pairs + lone_pair_delta[old.id])
                    if old.lone_pairs
                    else 0,
                    step=step,
                    chiral=0 if charge_delta[old.id] else old.chiral,
                )
            )
    old_connections = {
        frozenset((b.start, b.end)): b
        for b in bonds.values()
        if b.start in selected_atoms and b.end in selected_atoms
    }
    for connection in set(old_connections) | set(bond_delta):
        old = old_connections.get(connection)
        order = (old.order if old else 0) + bond_delta[connection]
        if not 0 <= order <= 3:
            raise ValueError(
                "This flow would create an unsupported bond order. Adjust the electron arrows."
            )
        if order == 0:
            continue
        first, last = (old.start, old.end) if old else sorted(connection)
        identity = new_id()
        result.bonds.append(
            Bond(
                identity,
                identities[first],
                identities[last],
                order,
                old.style if old and not bond_delta[connection] else "plain",
                old.aromatic if old else False,
                old.stereo if old and not bond_delta[connection] else 0,
                [identities[i] for i in old.stereo_atoms]
                if old and not bond_delta[connection]
                else [],
            )
        )
    for source in document.sources:
        source_ids = [identities[i] for i in source.atom_ids if i in identities]
        if source_ids:
            result.sources.append(replace(source, atom_ids=source_ids))
    y = sum(atoms[i].y for i in selected_atoms) / len(selected_atoms)
    result.arrows.append(Arrow(new_id(), "reaction", right + 45, y, right + 160, y, 0))
    result.notes.append(
        Note(
            new_id(),
            f"Step {step + 1}",
            left + offset,
            min(atoms[i].y for i in selected_atoms) - 80,
        )
    )
    for identity, delta in charge_delta.items():
        if delta:
            changes.append(
                f"{atoms[identity].element} charge: {atoms[identity].charge:+d} → "
                f"{atoms[identity].charge + delta:+d}"
            )
    result.validate()
    return StepProposal(
        result, changes, step, set(identities.values()), atoms[next(iter(selected_atoms))].step
    )
