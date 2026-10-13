"""Editable chemistry and drawing data, independent of Qt and RDKit."""

import math
from dataclasses import dataclass, field
from uuid import uuid4

ELEMENTS = frozenset(
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn "
    "Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce "
    "Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn "
    "Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh "
    "Fl Mc Lv Ts Og".split()
)


def new_id() -> str:
    return uuid4().hex


def finite(*values) -> bool:
    try:
        return all(type(v) in (int, float) and math.isfinite(v) for v in values)
    except OverflowError:
        return False


@dataclass(frozen=True)
class Atom:
    id: str
    element: str
    x: float
    y: float
    charge: int = 0
    isotope: int = 0
    hydrogens: int = -1
    label: str = ""
    radicals: int = 0
    lone_pairs: int = 0
    chiral: int = 0
    aromatic: bool = False
    identity: str = ""
    step: int = 0


@dataclass(frozen=True)
class Bond:
    id: str
    start: str
    end: str
    order: int = 1
    style: str = "plain"
    aromatic: bool = False
    stereo: int = 0
    stereo_atoms: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Source:
    query: str
    provider: str
    smiles: str
    atom_ids: list[str]


@dataclass(frozen=True)
class Arrow:
    id: str
    kind: str
    x1: float
    y1: float
    x2: float
    y2: float
    curvature: float = 40
    start_anchor: str = ""
    end_anchor: str = ""
    electrons: int = 2
    label: str = ""
    label_side: str = "auto"
    label_offset: float = 24
    start_group: list[str] = field(default_factory=list)
    end_group: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Note:
    id: str
    text: str
    x: float
    y: float
    size: int = 18


@dataclass
class Document:
    title: str = "Untitled"
    atoms: list[Atom] = field(default_factory=list)
    bonds: list[Bond] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    arrows: list[Arrow] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)

    def validate(self) -> None:
        if not isinstance(self.title, str):
            raise ValueError("Document title must be text.")
        ids: set[str] = set()
        for entity in [*self.atoms, *self.bonds, *self.arrows, *self.notes]:
            if not isinstance(entity.id, str) or not entity.id or entity.id in ids:
                raise ValueError("Entity IDs must be nonempty, unique strings.")
            ids.add(entity.id)
        for atom in self.atoms:
            if not isinstance(atom.element, str) or atom.element not in ELEMENTS:
                raise ValueError(f"Unsupported element on atom {atom.id}.")
            if not finite(atom.x, atom.y):
                raise ValueError("Atom coordinates must be finite numbers.")
            for value in (
                atom.charge,
                atom.isotope,
                atom.hydrogens,
                atom.radicals,
                atom.lone_pairs,
                atom.chiral,
                atom.step,
            ):
                if type(value) is not int:
                    raise ValueError("Atom properties must be integers.")
            if min(atom.isotope, atom.radicals, atom.lone_pairs, atom.step) < 0:
                raise ValueError("Isotope, electron counts and step must be nonnegative.")
            if atom.hydrogens < -1 or atom.chiral not in (0, 1, 2):
                raise ValueError("Invalid hydrogen count or stereochemistry.")
            if not isinstance(atom.label, str) or not isinstance(atom.identity, str):
                raise ValueError("Labels and identities must be strings.")
            if type(atom.aromatic) is not bool:
                raise ValueError("Aromatic flags must be boolean.")
        atom_ids = {atom.id for atom in self.atoms}
        connections: set[frozenset[str]] = set()
        for bond in self.bonds:
            if not isinstance(bond.start, str) or not isinstance(bond.end, str):
                raise ValueError("Bond endpoints must be atom IDs.")
            if bond.start not in atom_ids or bond.end not in atom_ids or bond.start == bond.end:
                raise ValueError("Bonds must connect two existing, different atoms.")
            if type(bond.order) is not int or bond.order not in (1, 2, 3):
                raise ValueError("Bond order must be 1, 2, or 3.")
            if bond.style not in ("plain", "wedge", "hash", "wavy"):
                raise ValueError("Unsupported bond style.")
            if type(bond.aromatic) is not bool or type(bond.stereo) is not int:
                raise ValueError("Invalid bond stereochemistry.")
            if bond.stereo not in (0, 1, 2, 3, 4, 5):
                raise ValueError("Unsupported bond stereo value.")
            if (
                not isinstance(bond.stereo_atoms, list)
                or any(not isinstance(a, str) or a not in atom_ids for a in bond.stereo_atoms)
                or len(bond.stereo_atoms) not in (0, 2)
            ):
                raise ValueError("Invalid bond stereo references.")
            connection = frozenset((bond.start, bond.end))
            if connection in connections:
                raise ValueError("Two atoms cannot have duplicate bond records.")
            connections.add(connection)
        for source in self.sources:
            if not all(isinstance(v, str) for v in (source.query, source.provider, source.smiles)):
                raise ValueError("Source metadata must be text.")
            if not isinstance(source.atom_ids, list) or any(
                not isinstance(a, str) or a not in atom_ids for a in source.atom_ids
            ):
                raise ValueError("Source references a missing atom.")

        anchors = {a.id for a in self.atoms} | {b.id for b in self.bonds}
        for arrow in self.arrows:
            if arrow.kind not in ("reaction", "equilibrium", "retro", "electron"):
                raise ValueError("Unsupported arrow kind.")
            if not finite(arrow.x1, arrow.y1, arrow.x2, arrow.y2, arrow.curvature):
                raise ValueError("Arrow geometry must be finite.")
            if type(arrow.electrons) is not int or arrow.electrons not in (1, 2):
                raise ValueError("Electron arrows must carry one or two electrons.")
            for anchor in (arrow.start_anchor, arrow.end_anchor):
                if not isinstance(anchor, str) or anchor and anchor not in anchors:
                    raise ValueError("Arrow anchor references a missing atom or bond.")
            if not isinstance(arrow.label, str) or arrow.label_side not in (
                "auto",
                "above",
                "below",
                "left",
                "right",
            ):
                raise ValueError("Invalid arrow caption or placement.")
            if not finite(arrow.label_offset) or not 8 <= arrow.label_offset <= 200:
                raise ValueError("Arrow caption offset must be between 8 and 200.")
            for group in (arrow.start_group, arrow.end_group):
                if not isinstance(group, list) or any(
                    not isinstance(i, str) or i not in atom_ids for i in group
                ):
                    raise ValueError("Pathway arrow references a missing molecule atom.")
                if len(group) != len(set(group)):
                    raise ValueError("Pathway groups must have unique atom IDs.")
            if bool(arrow.start_group) != bool(arrow.end_group) or set(arrow.start_group) & set(
                arrow.end_group
            ):
                raise ValueError("Pathway arrows require two separate molecule groups.")
            if arrow.start_group and arrow.kind == "electron":
                raise ValueError("Electron arrows use atom/bond anchors, not molecule groups.")
        for note in self.notes:
            if not isinstance(note.text, str) or not finite(note.x, note.y):
                raise ValueError("Invalid text annotation.")
            if type(note.size) is not int or not 8 <= note.size <= 96:
                raise ValueError("Text size must be between 8 and 96.")
