import json
import tempfile
import unittest
from pathlib import Path

from url_auto_opener.state import StateRepository


class StateRepositoryTests(unittest.TestCase):
    def test_common_paths_none_is_normalized_to_empty_list(self) -> None:
        repository = StateRepository(Path("sites.json"))

        state = repository.normalize_data({"sites": [], "common_paths": None})

        self.assertEqual(state.common_paths, [])
        self.assertEqual(len(state.sites), 1)

    def test_invalid_common_paths_type_raises_value_error(self) -> None:
        repository = StateRepository(Path("sites.json"))

        with self.assertRaises(ValueError):
            repository.normalize_data({"sites": [], "common_paths": "robots.txt"})

    def test_invalid_state_file_is_backed_up_on_next_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "sites.json"
            state_file.write_text("{ broken json", encoding="utf-8")

            repository = StateRepository(state_file)
            result = repository.load_state()

            self.assertIsNotNone(result.warning)
            self.assertTrue(state_file.exists())
            self.assertEqual(state_file.read_text(encoding="utf-8"), "{ broken json")

            repository.save_state(result.state)

            backups = list(Path(temp_dir).glob("sites.invalid-*.json"))
            self.assertEqual(len(backups), 1)

            saved_data = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertIn("sites", saved_data)
            self.assertIn("common_paths", saved_data)


if __name__ == "__main__":
    unittest.main()
