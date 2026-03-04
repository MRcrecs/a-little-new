import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .models import AppState, LoadStateResult, Site


class StateRepository:
    def __init__(self, state_file: Path | None = None) -> None:
        self.state_file = Path(state_file) if state_file is not None else self.get_default_state_file()
        self.pending_backup = False

    @staticmethod
    def get_default_state_file() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).with_name("sites.json")
        return Path(__file__).resolve().parent.parent / "sites.json"

    def generate_site_name(self, sites: Sequence[Site]) -> str:
        return self.generate_unique_name("Новый сайт", sites)

    @staticmethod
    def _normalize_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        if isinstance(value, (int, float)):
            return bool(value)
        return False

    def generate_unique_name(self, base_name: str, sites: Sequence[Site]) -> str:
        normalized_base_name = base_name.strip() or "Сайт"
        existing_names = {site.name.strip() for site in sites}
        if normalized_base_name not in existing_names:
            return normalized_base_name

        index = 2
        while f"{normalized_base_name} {index}" in existing_names:
            index += 1
        return f"{normalized_base_name} {index}"

    def generate_clone_name(self, source_site: Site, sites: Sequence[Site]) -> str:
        source_name = source_site.name.strip() or "Сайт"
        return self.generate_unique_name(f"Копия {source_name}", sites)

    def create_empty_site(self, sites: Sequence[Site]) -> Site:
        return Site(name=self.generate_site_name(sites))

    def create_default_state(self) -> AppState:
        return AppState(sites=[self.create_empty_site([])], common_paths=[])

    def normalize_site(self, raw_site: dict, fallback_index: int) -> Site:
        if not isinstance(raw_site, dict):
            raise ValueError("Каждый сайт должен быть объектом.")

        paths = raw_site.get("paths", [])
        if not isinstance(paths, list):
            raise ValueError("Поле 'paths' должно быть списком.")

        name = str(raw_site.get("name", "")).strip() or f"Сайт {fallback_index}"
        return Site(
            name=name,
            category=str(raw_site.get("category", "")).strip(),
            base_url=str(raw_site.get("base_url", "")).strip(),
            manager_url=str(raw_site.get("manager_url", "")).strip(),
            paths=[str(path).strip() for path in paths if str(path).strip()],
            favorite=self._normalize_bool(raw_site.get("favorite", False)),
        )

    def normalize_data(self, data: dict) -> AppState:
        if not isinstance(data, dict):
            raise ValueError("JSON должен содержать объект.")

        raw_common_paths = data.get("common_paths", [])
        if raw_common_paths is None:
            raw_common_paths = []
        elif not isinstance(raw_common_paths, list):
            raise ValueError("Поле 'common_paths' должно быть списком.")
        common_paths = [str(path).strip() for path in raw_common_paths if str(path).strip()]

        if "sites" in data:
            raw_sites = data["sites"]
            if not isinstance(raw_sites, list):
                raise ValueError("Поле 'sites' должно быть списком.")
            sites = [self.normalize_site(site, index) for index, site in enumerate(raw_sites, start=1)]
        elif "main_url" in data or "paths" in data:
            sites = [
                self.normalize_site(
                    {
                        "name": "Импортированный сайт",
                        "base_url": data.get("main_url", ""),
                        "manager_url": data.get("manager_url", ""),
                        "paths": data.get("paths", []),
                    },
                    1,
                )
            ]
        else:
            raise ValueError("JSON не содержит данных сайтов.")

        if not sites:
            sites = [self.create_empty_site([])]

        return AppState(sites=sites, common_paths=common_paths)

    @staticmethod
    def serialize_site(site: Site) -> dict:
        return {
            "name": site.name,
            "category": site.category,
            "base_url": site.base_url,
            "manager_url": site.manager_url,
            "paths": list(site.paths),
            "favorite": site.favorite,
        }

    def serialize_state(self, state: AppState) -> dict:
        return {
            "sites": [self.serialize_site(site) for site in state.sites],
            "common_paths": list(state.common_paths),
        }

    def save_json_file(self, file_path: Path | str, state: AppState) -> None:
        Path(file_path).write_text(
            json.dumps(self.serialize_state(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_json_file(self, file_path: Path | str) -> AppState:
        data = json.loads(Path(file_path).read_text(encoding="utf-8"))
        return self.normalize_data(data)

    def backup_existing_state_file(self) -> None:
        if not self.state_file.exists():
            self.pending_backup = False
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = self.state_file.with_name(f"{self.state_file.stem}.invalid-{timestamp}{self.state_file.suffix}")
        suffix_index = 2
        while backup_path.exists():
            backup_path = self.state_file.with_name(
                f"{self.state_file.stem}.invalid-{timestamp}-{suffix_index}{self.state_file.suffix}"
            )
            suffix_index += 1

        self.state_file.replace(backup_path)
        self.pending_backup = False

    def load_state(self) -> LoadStateResult:
        if self.state_file.exists():
            try:
                state = self.load_json_file(self.state_file)
                self.pending_backup = False
                return LoadStateResult(state=state)
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
                self.pending_backup = True
                return LoadStateResult(
                    state=self.create_default_state(),
                    warning=(
                        "Не удалось загрузить JSON:\n"
                        f"{error}\n\n"
                        "Исходный файл не будет перезаписан автоматически. "
                        "Перед следующим сохранением приложение сделает его резервную копию."
                    ),
                )

        return LoadStateResult(state=self.create_default_state())

    def save_state(self, state: AppState) -> None:
        if self.pending_backup:
            self.backup_existing_state_file()
        self.save_json_file(self.state_file, state)
