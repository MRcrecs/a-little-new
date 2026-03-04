import json
import tempfile
import unittest
from pathlib import Path

from url_auto_opener.models import Site
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

    def test_favorite_is_loaded_and_saved(self) -> None:
        repository = StateRepository(Path("sites.json"))

        state = repository.normalize_data(
            {
                "sites": [
                    {
                        "name": "Example",
                        "category": "MODX",
                        "base_url": "https://example.com",
                        "manager_url": "",
                        "paths": ["robots.txt"],
                        "favorite": True,
                    }
                ],
                "common_paths": [],
            }
        )

        self.assertTrue(state.sites[0].favorite)

        serialized = repository.serialize_state(state)
        self.assertTrue(serialized["sites"][0]["favorite"])

    def test_generate_clone_name_is_unique(self) -> None:
        repository = StateRepository(Path("sites.json"))
        sites = [Site(name="Site A"), Site(name="Копия Site A")]

        clone_name = repository.generate_clone_name(sites[0], sites)

        self.assertEqual(clone_name, "Копия Site A 2")

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
