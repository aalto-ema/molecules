import pytest
from rdkit import Chem

from molecules.chemistry.adapter import from_smiles, to_mol
from molecules.chemistry.resolver import resolve
from molecules.storage.native import load_document, save_document


@pytest.mark.parametrize(
    "smiles", ["CCO", "c1ccncc1", "[13CH3][NH3+]", "N[C@@H](C)C(=O)O", "F/C=C/F"]
)
def test_chemical_round_trip(smiles, tmp_path):
    document = from_smiles(smiles)
    path = tmp_path / "molecule.json"
    save_document(document, path)
    document = load_document(path)
    assert Chem.MolToSmiles(to_mol(document)) == Chem.MolToSmiles(Chem.MolFromSmiles(smiles))


def test_common_name_is_offline():
    document, warning = resolve("aspirin")
    assert len(document.atoms) == 13
    assert "offline" in document.sources[0].provider
    assert not warning


def test_invalid_smiles_does_not_create_a_document():
    with pytest.raises(ValueError):
        from_smiles("not a structure")


def test_resolver_failure_keeps_failure_explicit(monkeypatch):
    from urllib.error import URLError

    import molecules.chemistry.resolver as provider

    def unavailable(*args, **kwargs):
        raise URLError("offline")

    monkeypatch.setattr(provider, "urlopen", unavailable)
    with pytest.raises(ValueError, match="unavailable"):
        resolve("2-methylpropanoic acid")


def test_resolver_encodes_names_and_records_remote_provenance(monkeypatch):
    import io

    import molecules.chemistry.resolver as provider

    urls = []

    def response(request, timeout):
        urls.append(request.full_url)
        assert timeout == 12
        return io.BytesIO(b'{"status":"SUCCESS","smiles":"CCO"}')

    monkeypatch.setattr(provider, "urlopen", response)
    document, _ = resolve("ethan-1-ol example")
    assert "ethan-1-ol%20example.json" in urls[0]
    assert document.sources[0].query == "ethan-1-ol example"
    assert "OPSIN" in document.sources[0].provider
