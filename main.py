import json
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MODX URL Helper")
        self.resize(1100, 620)

        self.state_file = self.get_state_file_path()
        self.sites: list[dict] = []
        self.common_paths: list[str] = []
        self.filtered_site_indices: list[int] = []
        self.current_site_index = -1
        self.is_loading_site = False
        self.path_rows: list[tuple[QWidget, QLineEdit]] = []
        self.common_path_rows: list[tuple[QWidget, QLineEdit]] = []

        self.setup_ui()
        self.load_state()

    @staticmethod
    def get_state_file_path() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).with_name("sites.json")
        return Path(__file__).with_name("sites.json")

    def setup_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        actions_layout = QHBoxLayout()

        import_button = QPushButton("Импорт JSON")
        import_button.clicked.connect(self.import_json)
        actions_layout.addWidget(import_button)

        export_button = QPushButton("Экспорт JSON")
        export_button.clicked.connect(self.export_json)
        actions_layout.addWidget(export_button)

        save_button = QPushButton("Сохранить")
        save_button.clicked.connect(self.save_state)
        actions_layout.addWidget(save_button)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        left_layout.addWidget(QLabel("Сайты"))

        self.site_search_input = QLineEdit()
        self.site_search_input.setPlaceholderText("Поиск по названию или URL")
        self.site_search_input.textChanged.connect(self.refresh_site_list)
        left_layout.addWidget(self.site_search_input)

        self.category_filter = QComboBox()
        self.category_filter.currentIndexChanged.connect(self.refresh_site_list)
        left_layout.addWidget(self.category_filter)

        self.site_list = QListWidget()
        self.site_list.currentRowChanged.connect(self.on_site_selected)
        left_layout.addWidget(self.site_list)

        site_buttons_layout = QHBoxLayout()

        add_site_button = QPushButton("Добавить сайт")
        add_site_button.clicked.connect(self.add_site)
        site_buttons_layout.addWidget(add_site_button)

        delete_site_button = QPushButton("Удалить сайт")
        delete_site_button.clicked.connect(self.delete_site)
        site_buttons_layout.addWidget(delete_site_button)

        left_layout.addLayout(site_buttons_layout)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        tabs = QTabWidget()
        right_layout.addWidget(tabs)

        site_tab = QWidget()
        site_tab_layout = QVBoxLayout(site_tab)
        site_tab_layout.setContentsMargins(0, 0, 0, 0)
        site_tab_layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)

        self.site_name_input = QLineEdit()
        self.site_name_input.setPlaceholderText("Название сайта")
        self.site_name_input.textChanged.connect(self.save_current_site)
        form_layout.addRow("Название", self.site_name_input)

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Например: MODX Evo, MODX Revo, v2")
        self.category_input.textChanged.connect(self.save_current_site)
        form_layout.addRow("Категория", self.category_input)

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("https://example.com/")
        self.base_url_input.textChanged.connect(self.save_current_site)
        form_layout.addRow("Основная ссылка", self.base_url_input)

        self.manager_url_input = QLineEdit()
        self.manager_url_input.setPlaceholderText("https://example.com/manager/")
        self.manager_url_input.textChanged.connect(self.save_current_site)
        form_layout.addRow("Manager URL", self.manager_url_input)

        site_tab_layout.addLayout(form_layout)

        paths_header = QHBoxLayout()
        paths_header.addWidget(QLabel("Path"))
        paths_header.addStretch()

        add_path_button = QPushButton("+")
        add_path_button.setFixedWidth(40)
        add_path_button.clicked.connect(lambda: self.add_path_input())
        paths_header.addWidget(add_path_button)
        site_tab_layout.addLayout(paths_header)

        self.paths_container = QWidget()
        self.paths_layout = QVBoxLayout(self.paths_container)
        self.paths_layout.setContentsMargins(0, 0, 0, 0)
        self.paths_layout.setSpacing(8)
        self.paths_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setWidget(self.paths_container)
        site_tab_layout.addWidget(scroll)

        open_buttons_layout = QHBoxLayout()

        open_site_button = QPushButton("Открыть сайт")
        open_site_button.clicked.connect(self.open_site)
        open_buttons_layout.addWidget(open_site_button)

        open_manager_button = QPushButton("Открыть manager")
        open_manager_button.clicked.connect(self.open_manager)
        open_buttons_layout.addWidget(open_manager_button)

        open_paths_button = QPushButton("Открыть path")
        open_paths_button.clicked.connect(self.open_paths)
        open_buttons_layout.addWidget(open_paths_button)

        import_paths_button = QPushButton("Импорт path")
        import_paths_button.clicked.connect(self.import_paths_from_site)
        open_buttons_layout.addWidget(import_paths_button)

        site_tab_layout.addLayout(open_buttons_layout)

        common_paths_tab = QWidget()
        common_paths_layout = QVBoxLayout(common_paths_tab)
        common_paths_layout.setContentsMargins(0, 0, 0, 0)
        common_paths_layout.setSpacing(12)

        common_header = QHBoxLayout()
        common_header.addWidget(QLabel("Общий path"))
        common_header.addStretch()

        add_common_path_button = QPushButton("+")
        add_common_path_button.setFixedWidth(40)
        add_common_path_button.clicked.connect(lambda: self.add_common_path_input())
        common_header.addWidget(add_common_path_button)
        common_paths_layout.addLayout(common_header)

        self.common_paths_container = QWidget()
        self.common_paths_layout = QVBoxLayout(self.common_paths_container)
        self.common_paths_layout.setContentsMargins(0, 0, 0, 0)
        self.common_paths_layout.setSpacing(8)
        self.common_paths_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        common_scroll = QScrollArea()
        common_scroll.setWidgetResizable(True)
        common_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        common_scroll.setWidget(self.common_paths_container)
        common_paths_layout.addWidget(common_scroll)

        open_common_paths_button = QPushButton("Открыть общий path")
        open_common_paths_button.clicked.connect(self.open_category_path)
        common_paths_layout.addWidget(open_common_paths_button)

        tabs.addTab(site_tab, "Сайт")
        tabs.addTab(common_paths_tab, "Общий path")
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

    def create_empty_site(self) -> dict:
        return {
            "name": self.generate_site_name(),
            "category": "",
            "base_url": "",
            "manager_url": "",
            "paths": [],
        }

    def generate_site_name(self) -> str:
        base_name = "Новый сайт"
        existing_names = {site.get("name", "").strip() for site in self.sites}
        if base_name not in existing_names:
            return base_name

        index = 2
        while f"{base_name} {index}" in existing_names:
            index += 1
        return f"{base_name} {index}"

    def add_site(self) -> None:
        self.sites.append(self.create_empty_site())
        self.refresh_site_list(preferred_site_index=len(self.sites) - 1)
        self.save_state()

    def delete_site(self) -> None:
        if self.current_site_index < 0 or self.current_site_index >= len(self.sites):
            return

        answer = QMessageBox.question(
            self,
            "Удаление сайта",
            "Удалить выбранный сайт?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        del self.sites[self.current_site_index]

        if not self.sites:
            self.sites.append(self.create_empty_site())

        self.refresh_site_list(preferred_site_index=min(self.current_site_index, len(self.sites) - 1))
        self.save_state()

    def select_site_by_actual_index(self, actual_index: int) -> None:
        if actual_index in self.filtered_site_indices:
            self.site_list.setCurrentRow(self.filtered_site_indices.index(actual_index))
            return

        if self.filtered_site_indices:
            self.site_list.setCurrentRow(0)
            return

        self.current_site_index = -1
        self.load_site_into_form(None)

    def refresh_category_filter(self) -> None:
        current_value = self.category_filter.currentData()
        categories = sorted(
            {
                site.get("category", "").strip()
                for site in self.sites
                if site.get("category", "").strip()
            },
            key=str.lower,
        )

        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("Все категории", "")
        for category in categories:
            self.category_filter.addItem(category, category)

        target_index = self.category_filter.findData(current_value)
        self.category_filter.setCurrentIndex(target_index if target_index >= 0 else 0)
        self.category_filter.blockSignals(False)

    def refresh_site_list(self, *_args, preferred_site_index: int | None = None) -> None:
        search_query = self.site_search_input.text().strip().lower()
        selected_category = self.category_filter.currentData() or ""
        previous_site_index = self.current_site_index if preferred_site_index is None else preferred_site_index

        self.refresh_category_filter()
        selected_category = self.category_filter.currentData() or selected_category or ""

        self.filtered_site_indices = []
        self.site_list.blockSignals(True)
        self.site_list.clear()

        for index, site in enumerate(self.sites, start=1):
            zero_based_index = index - 1
            name = site.get("name", "").strip() or f"Сайт {index}"
            category = site.get("category", "").strip()
            base_url = site.get("base_url", "").strip()
            manager_url = site.get("manager_url", "").strip()
            if selected_category and category != selected_category:
                continue

            search_blob = " ".join([name, category, base_url, manager_url]).lower()
            if search_query and search_query not in search_blob:
                continue

            self.filtered_site_indices.append(zero_based_index)
            self.site_list.addItem(f"[{category}] {name}" if category else name)

        self.site_list.blockSignals(False)

        if not self.filtered_site_indices:
            self.current_site_index = -1
            self.load_site_into_form(None)
            return

        self.select_site_by_actual_index(previous_site_index)

    def on_site_selected(self, index: int) -> None:
        if index < 0 or index >= len(self.filtered_site_indices):
            self.current_site_index = -1
            self.load_site_into_form(None)
            return

        actual_index = self.filtered_site_indices[index]
        self.current_site_index = actual_index
        self.load_site_into_form(self.sites[actual_index])

    def load_site_into_form(self, site: dict | None) -> None:
        self.is_loading_site = True

        self.clear_path_inputs()

        if site is None:
            self.site_name_input.setText("")
            self.category_input.setText("")
            self.base_url_input.setText("")
            self.manager_url_input.setText("")
            self.add_path_input(save_after=False)
            self.is_loading_site = False
            return

        self.site_name_input.setText(str(site.get("name", "")))
        self.category_input.setText(str(site.get("category", "")))
        self.base_url_input.setText(str(site.get("base_url", "")))
        self.manager_url_input.setText(str(site.get("manager_url", "")))

        paths = site.get("paths", [])
        if isinstance(paths, list) and paths:
            for path in paths:
                self.add_path_input(str(path), save_after=False)
        else:
            self.add_path_input(save_after=False)

        self.is_loading_site = False

    def add_path_input(self, value: str = "", save_after: bool = True) -> None:
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        field = QLineEdit()
        field.setPlaceholderText("/page или section/item")
        field.setText(value)
        field.textChanged.connect(self.save_current_site)
        row_layout.addWidget(field)

        remove_button = QPushButton("x")
        remove_button.setFixedWidth(32)
        remove_button.clicked.connect(lambda _checked=False, widget=row_widget: self.remove_path_input(widget))
        row_layout.addWidget(remove_button)

        self.path_rows.append((row_widget, field))
        self.paths_layout.addWidget(row_widget)

        if save_after:
            self.save_current_site()

    def remove_path_input(self, row_widget: QWidget) -> None:
        if len(self.path_rows) == 1:
            self.path_rows[0][1].clear()
            self.save_current_site()
            return

        for index, (widget, _field) in enumerate(self.path_rows):
            if widget is row_widget:
                self.path_rows.pop(index)
                self.paths_layout.removeWidget(widget)
                widget.deleteLater()
                break

        self.save_current_site()

    def clear_path_inputs(self) -> None:
        while self.path_rows:
            row_widget, _field = self.path_rows.pop()
            self.paths_layout.removeWidget(row_widget)
            row_widget.deleteLater()

    def add_common_path_input(self, value: str = "", save_after: bool = True) -> None:
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        field = QLineEdit()
        field.setPlaceholderText("/page или section/item")
        field.setText(value)
        field.textChanged.connect(self.save_state)
        row_layout.addWidget(field)

        remove_button = QPushButton("x")
        remove_button.setFixedWidth(32)
        remove_button.clicked.connect(lambda _checked=False, widget=row_widget: self.remove_common_path_input(widget))
        row_layout.addWidget(remove_button)

        self.common_path_rows.append((row_widget, field))
        self.common_paths_layout.addWidget(row_widget)

        if save_after:
            self.save_state()

    def remove_common_path_input(self, row_widget: QWidget) -> None:
        if len(self.common_path_rows) == 1:
            self.common_path_rows[0][1].clear()
            self.save_state()
            return

        for index, (widget, _field) in enumerate(self.common_path_rows):
            if widget is row_widget:
                self.common_path_rows.pop(index)
                self.common_paths_layout.removeWidget(widget)
                widget.deleteLater()
                break

        self.save_state()

    def clear_common_path_inputs(self) -> None:
        while self.common_path_rows:
            row_widget, _field = self.common_path_rows.pop()
            self.common_paths_layout.removeWidget(row_widget)
            row_widget.deleteLater()

    def load_common_paths_into_form(self) -> None:
        self.clear_common_path_inputs()
        if self.common_paths:
            for path in self.common_paths:
                self.add_common_path_input(path, save_after=False)
        else:
            self.add_common_path_input(save_after=False)

    def collect_common_paths(self) -> list[str]:
        return [field.text().strip() for _widget, field in self.common_path_rows if field.text().strip()]

    def collect_site_from_form(self) -> dict:
        return {
            "name": self.site_name_input.text().strip() or self.generate_site_name(),
            "category": self.category_input.text().strip(),
            "base_url": self.base_url_input.text().strip(),
            "manager_url": self.manager_url_input.text().strip(),
            "paths": [field.text().strip() for _widget, field in self.path_rows if field.text().strip()],
        }

    def save_current_site(self) -> None:
        if self.is_loading_site:
            return

        if self.current_site_index < 0 or self.current_site_index >= len(self.sites):
            return

        self.sites[self.current_site_index] = self.collect_site_from_form()
        self.refresh_site_list(preferred_site_index=self.current_site_index)
        self.save_state()

    def normalize_site(self, raw_site: dict, fallback_index: int) -> dict:
        if not isinstance(raw_site, dict):
            raise ValueError("Каждый сайт должен быть объектом.")

        paths = raw_site.get("paths", [])
        if not isinstance(paths, list):
            raise ValueError("Поле 'paths' должно быть списком.")

        name = str(raw_site.get("name", "")).strip() or f"Сайт {fallback_index}"
        return {
            "name": name,
            "category": str(raw_site.get("category", "")).strip(),
            "base_url": str(raw_site.get("base_url", "")).strip(),
            "manager_url": str(raw_site.get("manager_url", "")).strip(),
            "paths": [str(path).strip() for path in paths if str(path).strip()],
        }

    def normalize_data(self, data: dict) -> dict:
        if not isinstance(data, dict):
            raise ValueError("JSON должен содержать объект.")

        raw_common_paths = data.get("common_paths", [])
        if raw_common_paths and not isinstance(raw_common_paths, list):
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
            sites = [self.create_empty_site()]

        return {"sites": sites, "common_paths": common_paths}

    def apply_data(self, data: dict) -> None:
        normalized = self.normalize_data(data)
        self.sites = normalized["sites"]
        self.common_paths = normalized["common_paths"]
        self.load_common_paths_into_form()
        self.refresh_site_list(preferred_site_index=0)
        self.save_state()

    def collect_data(self) -> dict:
        return {
            "sites": self.sites,
            "common_paths": self.collect_common_paths(),
        }

    def save_json_file(self, file_path: Path) -> None:
        file_path.write_text(
            json.dumps(self.collect_data(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_json_file(self, file_path: Path) -> None:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        self.apply_data(data)

    def save_state(self) -> None:
        try:
            self.save_json_file(self.state_file)
        except OSError as error:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить JSON:\n{error}")

    def load_state(self) -> None:
        if self.state_file.exists():
            try:
                self.load_json_file(self.state_file)
                return
            except (OSError, json.JSONDecodeError, ValueError) as error:
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить JSON:\n{error}")

        self.sites = [self.create_empty_site()]
        self.common_paths = []
        self.load_common_paths_into_form()
        self.refresh_site_list(preferred_site_index=0)
        self.save_state()

    def import_json(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт JSON",
            str(self.state_file.parent),
            "JSON Files (*.json)",
        )
        if not file_name:
            return

        try:
            self.load_json_file(Path(file_name))
            QMessageBox.information(self, "Импорт", "База сайтов успешно импортирована.")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            QMessageBox.warning(self, "Ошибка", f"Не удалось импортировать JSON:\n{error}")

    def export_json(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт JSON",
            str(self.state_file),
            "JSON Files (*.json)",
        )
        if not file_name:
            return

        try:
            self.save_json_file(Path(file_name))
            QMessageBox.information(self, "Экспорт", "База сайтов успешно экспортирована.")
        except OSError as error:
            QMessageBox.warning(self, "Ошибка", f"Не удалось экспортировать JSON:\n{error}")

    def import_paths_from_site(self) -> None:
        if self.current_site_index < 0 or self.current_site_index >= len(self.sites):
            QMessageBox.warning(self, "Ошибка", "Выберите текущий сайт.")
            return

        current_category = self.sites[self.current_site_index].get("category", "").strip()
        source_sites = self.get_source_sites_for_paths(current_category)
        if not source_sites:
            QMessageBox.information(self, "Импорт path", "Нет других сайтов для импорта.")
            return

        labels = [label for _index, label in source_sites]
        selected_label, accepted = QInputDialog.getItem(
            self,
            "Импорт path",
            "С какого сайта импортировать path:",
            labels,
            0,
            False,
        )
        if not accepted or not selected_label:
            return

        source_index = next(index for index, label in source_sites if label == selected_label)
        source_paths = self.sites[source_index].get("paths", [])
        current_paths = self.sites[self.current_site_index].get("paths", [])

        merged_paths: list[str] = []
        for path in [*current_paths, *source_paths]:
            normalized_path = str(path).strip()
            if normalized_path and normalized_path not in merged_paths:
                merged_paths.append(normalized_path)

        self.sites[self.current_site_index]["paths"] = merged_paths
        self.load_site_into_form(self.sites[self.current_site_index])
        self.save_current_site()
        QMessageBox.information(self, "Импорт path", "Path успешно импортированы.")

    def get_source_sites_for_paths(self, current_category: str) -> list[tuple[int, str]]:
        matching_sites = [
            (index, self.get_site_display_label(site, index))
            for index, site in enumerate(self.sites)
            if index != self.current_site_index and site.get("category", "").strip() == current_category and current_category
        ]
        if matching_sites:
            return matching_sites

        return [
            (index, self.get_site_display_label(site, index))
            for index, site in enumerate(self.sites)
            if index != self.current_site_index
        ]

    def get_site_display_label(self, site: dict, index: int) -> str:
        category = site.get("category", "").strip()
        name = site.get("name", "").strip() or f"Сайт {index + 1}"
        return f"{index + 1}. [{category}] {name}" if category else f"{index + 1}. {name}"

    def get_available_categories(self) -> list[str]:
        return sorted(
            {
                site.get("category", "").strip()
                for site in self.sites
                if site.get("category", "").strip()
            },
            key=str.lower,
        )

    def normalize_url(self, url: str) -> str:
        target = url.strip()
        if not target:
            return ""

        parsed = urlparse(target)
        if parsed.scheme in {"http", "https"}:
            return target

        return f"https://{target.lstrip('/')}"

    def build_url(self, base_url: str, path: str) -> str:
        normalized_base = self.normalize_url(base_url)
        if not normalized_base:
            return ""
        return urljoin(normalized_base.rstrip("/") + "/", path.lstrip("/"))

    def open_in_browser(self, url: str) -> None:
        webbrowser.get().open_new_tab(url)

    def open_url(self, url: str, error_message: str) -> None:
        target = self.normalize_url(url)
        if not target:
            QMessageBox.warning(self, "Ошибка", error_message)
            return
        self.open_in_browser(target)

    def open_site(self) -> None:
        self.open_url(self.base_url_input.text(), "Введите основную ссылку.")

    def open_manager(self) -> None:
        manager_url = self.manager_url_input.text().strip()
        if not manager_url:
            base_url = self.base_url_input.text().strip()
            manager_url = self.build_url(base_url, "manager/") if base_url else ""

        self.open_url(manager_url, "Введите Manager URL или основную ссылку.")

    def open_paths(self) -> None:
        base_url = self.normalize_url(self.base_url_input.text())
        if not base_url:
            QMessageBox.warning(self, "Ошибка", "Введите основную ссылку.")
            return

        paths = [field.text().strip() for _widget, field in self.path_rows if field.text().strip()]
        if not paths:
            self.open_in_browser(base_url)
            return

        for path in paths:
            self.open_in_browser(self.build_url(base_url, path))

    def open_category_path(self) -> None:
        categories = self.get_available_categories()
        if not categories:
            QMessageBox.warning(self, "Ошибка", "Нет категорий для выбора.")
            return

        category, accepted = QInputDialog.getItem(
            self,
            "Выберите категорию",
            "Категория:",
            categories,
            0,
            False,
        )
        if not accepted or not category:
            return

        paths = self.collect_common_paths()
        if not paths:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы один общий path.")
            return

        matching_sites = [
            site for site in self.sites
            if site.get("category", "").strip() == category and self.normalize_url(site.get("base_url", ""))
        ]
        if not matching_sites:
            QMessageBox.warning(self, "Ошибка", "В этой категории нет сайтов с основной ссылкой.")
            return

        for site in matching_sites:
            for path in paths:
                self.open_in_browser(self.build_url(site.get("base_url", ""), path))


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
