import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from molecules.domain.document import Atom, Bond, Document  # noqa: E402
from molecules.storage.native import load_document, save_document  # noqa: E402


class NativeDocumentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "test.molecules.json"
        self.document = Document(
            title="Charged structure — test",
            atoms=[Atom("a1", "N", -12.5, 0, 1), Atom("a2", "C", 20, 30)],
            bonds=[Bond("b1", "a1", "a2", 2)],
        )

    def write_payload(self, payload):
        self.path.write_text(json.dumps(payload), encoding="utf-8")

    def payload(self):
        save_document(self.document, self.path)
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_round_trip_preserves_positions_charges_orders_and_title(self):
        save_document(self.document, self.path)
        self.assertEqual(load_document(self.path), self.document)

    def test_empty_document_round_trip(self):
        save_document(Document(), self.path)
        self.assertEqual(load_document(self.path), Document())

    def test_future_version_is_rejected_and_file_unchanged(self):
        payload = self.payload()
        payload["schema_version"] = 99
        self.write_payload(payload)
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "version"):
            load_document(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_graphs_are_rejected(self):
        for bonds in (
            [Bond("b1", "a1", "missing")],
            [Bond("b1", "a1", "a1")],
            [Bond("b1", "a1", "a2"), Bond("b2", "a2", "a1")],
        ):
            with self.subTest(bonds=bonds), self.assertRaises(ValueError):
                Document(atoms=self.document.atoms, bonds=bonds).validate()

    def test_bad_atom_fields_are_rejected(self):
        for atom in (
            Atom("a", "Q", 0, 0),
            Atom("a", "C", float("nan"), 0),
            Atom("a", "C", True, 0),
            Atom("a", "C", 0, 0, True),
        ):
            with self.subTest(atom=atom), self.assertRaises(ValueError):
                Document(atoms=[atom]).validate()

    def test_duplicate_ids_across_entity_types_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            Document(atoms=self.document.atoms, bonds=[Bond("a1", "a1", "a2")]).validate()

    def test_unknown_data_is_not_silently_dropped(self):
        payload = self.payload()
        payload["unsupported_entities"] = []
        self.write_payload(payload)
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            load_document(self.path)

    def test_duplicate_json_keys_are_rejected(self):
        self.path.write_text('{"schema_version": 1, "schema_version": 2}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            load_document(self.path)

    def test_failed_save_preserves_existing_file(self):
        save_document(self.document, self.path)
        before = self.path.read_bytes()
        self.document.bonds = [Bond("b1", "a1", "missing")]
        with self.assertRaises(ValueError):
            save_document(self.document, self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_example_opens(self):
        example = Path(__file__).resolve().parents[1] / "examples" / "ethanol.molecules.json"
        document = load_document(example)
        self.assertEqual((len(document.atoms), len(document.bonds)), (3, 2))


if __name__ == "__main__":
    unittest.main()
