"""RDKit conversion, with drawing state kept in the domain model."""

from dataclasses import replace

from rdkit import Chem
from rdkit.Chem import rdDepictor

from molecules.domain.document import Atom, Bond, Document, new_id


def from_smiles(smiles: str, title: str = "Structure") -> Document:
    if not smiles.strip() or len(smiles) > 20000:
        raise ValueError("Enter a nonempty SMILES string of at most 20,000 characters.")
    parameters = Chem.SmilesParserParams()
    parameters.removeHs = False
    mol = Chem.MolFromSmiles(smiles, parameters)
    if mol is None or not mol.GetNumAtoms():
        raise ValueError("This SMILES could not be parsed. Check atom and ring notation.")
    if mol.GetNumAtoms() > 1000:
        raise ValueError("Please insert structures with at most 1,000 atoms at a time.")
    rdDepictor.Compute2DCoords(mol)
    aromatic_atoms = {a.GetIdx() for a in mol.GetAtoms() if a.GetIsAromatic()}
    aromatic_bonds = {b.GetIdx() for b in mol.GetBonds() if b.GetIsAromatic()}
    Chem.Kekulize(mol, clearAromaticFlags=True)
    Chem.WedgeMolBonds(mol, mol.GetConformer())
    ids = [new_id() for _ in mol.GetAtoms()]
    atoms = []
    for a in mol.GetAtoms():
        p = mol.GetConformer().GetAtomPosition(a.GetIdx())
        atoms.append(
            Atom(
                ids[a.GetIdx()],
                a.GetSymbol(),
                p.x * 40,
                -p.y * 40,
                a.GetFormalCharge(),
                a.GetIsotope(),
                a.GetNumExplicitHs() if a.GetNoImplicit() else -1,
                radicals=a.GetNumRadicalElectrons(),
                chiral=int(a.GetChiralTag()),
                aromatic=a.GetIdx() in aromatic_atoms,
                identity=ids[a.GetIdx()],
            )
        )
    bonds = []
    for b in mol.GetBonds():
        order = b.GetBondTypeAsDouble()
        if order not in (1, 2, 3):
            raise ValueError("This structure has a bond type the editor cannot represent yet.")
        style = {Chem.BondDir.BEGINWEDGE: "wedge", Chem.BondDir.BEGINDASH: "hash"}.get(
            b.GetBondDir(), "plain"
        )
        bonds.append(
            Bond(
                new_id(),
                ids[b.GetBeginAtomIdx()],
                ids[b.GetEndAtomIdx()],
                int(order),
                style,
                b.GetIdx() in aromatic_bonds,
                int(b.GetStereo()),
                [ids[i] for i in b.GetStereoAtoms()],
            )
        )
    document = Document(title, atoms, bonds)
    document.validate()
    return document


def to_mol(document: Document):
    document.validate()
    builder = Chem.RWMol()
    ids = {}
    for a in document.atoms:
        atom = Chem.Atom(a.element)
        atom.SetFormalCharge(a.charge)
        atom.SetIsotope(a.isotope)
        atom.SetNumRadicalElectrons(a.radicals)
        atom.SetChiralTag(Chem.ChiralType(a.chiral))
        atom.SetIsAromatic(a.aromatic)
        if a.hydrogens >= 0:
            atom.SetNoImplicit(True)
            atom.SetNumExplicitHs(a.hydrogens)
        ids[a.id] = builder.AddAtom(atom)
    for b in document.bonds:
        builder.AddBond(
            ids[b.start],
            ids[b.end],
            Chem.BondType.AROMATIC
            if b.aromatic
            else {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE, 3: Chem.BondType.TRIPLE}[
                b.order
            ],
        )
        bond = builder.GetBondBetweenAtoms(ids[b.start], ids[b.end])
        if b.style in ("wedge", "hash"):
            bond.SetBondDir(
                Chem.BondDir.BEGINWEDGE if b.style == "wedge" else Chem.BondDir.BEGINDASH
            )
    mol = builder.GetMol()
    conf = Chem.Conformer(len(document.atoms))
    for a in document.atoms:
        conf.SetAtomPosition(ids[a.id], (a.x / 40, -a.y / 40, 0))
    mol.AddConformer(conf)
    Chem.SanitizeMol(mol)
    for b in document.bonds:
        bond = mol.GetBondBetweenAtoms(ids[b.start], ids[b.end])
        if b.stereo_atoms:
            bond.SetStereoAtoms(*(ids[a] for a in b.stereo_atoms))
        bond.SetStereo(Chem.BondStereo(b.stereo))
    Chem.AssignChiralTypesFromBondDirs(mol, replaceExistingTags=True)
    Chem.SetDoubleBondNeighborDirections(mol)
    Chem.AssignStereochemistry(mol, cleanIt=False, force=True)
    return mol


def chemistry_warning(document: Document) -> str:
    try:
        to_mol(document)
        return ""
    except (ValueError, RuntimeError) as exc:
        return f"Check chemistry: {str(exc).splitlines()[0]}"


def clean_layout(document: Document) -> Document:
    mol = to_mol(document)
    rdDepictor.Compute2DCoords(mol)
    positions = mol.GetConformer()
    old_x = sum(a.x for a in document.atoms) / max(1, len(document.atoms))
    old_y = sum(a.y for a in document.atoms) / max(1, len(document.atoms))
    result = replace(
        document,
        atoms=[
            replace(
                a,
                x=positions.GetAtomPosition(i).x * 40 + old_x,
                y=-positions.GetAtomPosition(i).y * 40 + old_y,
            )
            for i, a in enumerate(document.atoms)
        ],
    )
    return result
