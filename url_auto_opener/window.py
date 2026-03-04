from collections.abc import Sequence

from PyQt6.QtCore import QThread, Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QCheckBox,
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

from .models import (
    AppState,
    CommonPathCheckRequest,
    CommonPathSiteRequest,
    Site,
    SitePathCheckRequest,
)
from .state import StateRepository
from .url_service import UrlService
from .workers import CommonPathCheckWorker, SitePathCheckWorker


class MainWindow(QMainWindow):
    def __init__(self, state_repository: StateRepository, url_service: UrlService) -> None:
        super().__init__()
        self.state_repository = state_repository
        self.url_service = url_service

        self.setWindowTitle("MODX URL Helper")
        self.resize(1100, 620)

        self.state = AppState()
        self.filtered_site_indices: list[int] = []
        self.current_site_index = -1
        self.is_loading_site = False
        self.path_rows: list[tuple[QWidget, QLineEdit, QLabel]] = []
        self.common_path_rows: list[tuple[QWidget, QLineEdit, QLabel, QPushButton, QLabel]] = []
        self.site_check_thread: QThread | None = None
        self.site_check_worker: SitePathCheckWorker | None = None
        self.common_check_thread: QThread | None = None
        self.common_check_worker: CommonPathCheckWorker | None = None

        self.setup_ui()
        self.load_state()

    @property
    def sites(self) -> list[Site]:
        return self.state.sites

    @property
    def common_paths(self) -> list[str]:
        return self.state.common_paths

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

        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        left_layout.addWidget(QLabel("Сайты"))

        self.site_search_input = QLineEdit()
        self.site_search_input.setPlaceholderText("Поиск по названию или URL")
        self.site_search_input.textChanged.connect(self.refresh_site_list)
        left_layout.addWidget(self.site_search_input)

        self.sort_mode_filter = QComboBox()
        self.sort_mode_filter.addItem("По порядку добавления", "added")
        self.sort_mode_filter.addItem("Избранные сверху", "favorite")
        self.sort_mode_filter.addItem("По имени", "name")
        self.sort_mode_filter.setCurrentIndex(0)
        self.sort_mode_filter.currentIndexChanged.connect(self.refresh_site_list)
        left_layout.addWidget(self.sort_mode_filter)

        self.category_filter = QComboBox()
        self.category_filter.addItem("Все категории", "")
        self.category_filter.setCurrentIndex(0)
        self.category_filter.currentIndexChanged.connect(self.refresh_site_list)
        left_layout.addWidget(self.category_filter)

        self.site_list = QListWidget()
        self.site_list.currentRowChanged.connect(self.on_site_selected)
        left_layout.addWidget(self.site_list)

        site_buttons_layout = QHBoxLayout()

        add_site_button = QPushButton("Добавить сайт")
        add_site_button.clicked.connect(self.add_site)
        site_buttons_layout.addWidget(add_site_button)

        clone_site_button = QPushButton("Клонировать сайт")
        clone_site_button.clicked.connect(self.clone_site)
        site_buttons_layout.addWidget(clone_site_button)

        delete_site_button = QPushButton("Удалить сайт")
        delete_site_button.clicked.connect(self.delete_site)
        site_buttons_layout.addWidget(delete_site_button)

        left_layout.addLayout(site_buttons_layout)
        splitter.addWidget(self.left_panel)

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

        self.favorite_checkbox = QCheckBox("Избранный")
        self.favorite_checkbox.stateChanged.connect(self.save_current_site)
        form_layout.addRow("Статус", self.favorite_checkbox)

        site_tab_layout.addLayout(form_layout)

        paths_header = QHBoxLayout()
        paths_header.addWidget(QLabel("Path"))
        paths_header.addStretch()

        self.add_path_button = QPushButton("+")
        self.add_path_button.setFixedWidth(40)
        self.add_path_button.clicked.connect(lambda: self.add_path_input())
        paths_header.addWidget(self.add_path_button)

        self.bulk_add_paths_button = QPushButton("Массово")
        self.bulk_add_paths_button.clicked.connect(self.bulk_add_paths)
        paths_header.addWidget(self.bulk_add_paths_button)
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

        self.check_paths_button = QPushButton("Проверить path")
        self.check_paths_button.clicked.connect(self.check_site_paths)
        open_buttons_layout.addWidget(self.check_paths_button)

        site_tab_layout.addLayout(open_buttons_layout)

        common_paths_tab = QWidget()
        common_paths_layout = QVBoxLayout(common_paths_tab)
        common_paths_layout.setContentsMargins(0, 0, 0, 0)
        common_paths_layout.setSpacing(12)

        common_header = QHBoxLayout()
        common_header.addWidget(QLabel("Общий path"))
        common_header.addStretch()

        self.add_common_path_button = QPushButton("+")
        self.add_common_path_button.setFixedWidth(40)
        self.add_common_path_button.clicked.connect(lambda: self.add_common_path_input())
        common_header.addWidget(self.add_common_path_button)

        self.bulk_add_common_paths_button = QPushButton("Массово")
        self.bulk_add_common_paths_button.clicked.connect(self.bulk_add_common_paths)
        common_header.addWidget(self.bulk_add_common_paths_button)
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

        self.check_common_paths_button = QPushButton("Проверить общий path")
        self.check_common_paths_button.clicked.connect(self.check_common_paths_by_category)
        common_paths_layout.addWidget(self.check_common_paths_button)

        tabs.addTab(site_tab, "Сайт")
        tabs.addTab(common_paths_tab, "Общий path")
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

    def create_empty_site(self) -> Site:
        return self.state_repository.create_empty_site(self.sites)

    def generate_site_name(self) -> str:
        return self.state_repository.generate_site_name(self.sites)

    def add_site(self) -> None:
        self.sites.append(self.create_empty_site())
        self.refresh_site_list(preferred_site_index=len(self.sites) - 1)
        self.save_state()

    def clone_site(self) -> None:
        if self.current_site_index < 0 or self.current_site_index >= len(self.sites):
            QMessageBox.warning(self, "Ошибка", "Выберите сайт для клонирования.")
            return

        source_site = self.sites[self.current_site_index]
        cloned_site = Site(
            name=self.state_repository.generate_clone_name(source_site, self.sites),
            category=source_site.category,
            base_url=source_site.base_url,
            manager_url=source_site.manager_url,
            paths=list(source_site.paths),
            favorite=False,
        )
        self.sites.append(cloned_site)
        self.refresh_site_list(preferred_site_index=len(self.sites) - 1)
        self.save_state()

    def delete_site(self) -> None:
        if self.current_site_index < 0 or self.current_site_index >= len(self.sites):
            return

        answer = QMessageBox.question(self, "Удаление сайта", "Удалить выбранный сайт?")
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
        categories = sorted({site.category.strip() for site in self.sites if site.category.strip()}, key=str.lower)

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
        sort_mode = self.sort_mode_filter.currentData() or "favorite"
        previous_site_index = self.current_site_index if preferred_site_index is None else preferred_site_index

        self.refresh_category_filter()
        selected_category = self.category_filter.currentData() or selected_category or ""

        self.filtered_site_indices = []
        self.site_list.blockSignals(True)
        self.site_list.clear()

        indexed_sites = list(enumerate(self.sites))
        if sort_mode == "name":
            indexed_sites.sort(key=lambda item: ((item[1].name.strip() or f"Сайт {item[0] + 1}").lower(), item[0]))
        elif sort_mode == "added":
            pass
        else:
            indexed_sites.sort(
                key=lambda item: (
                    not item[1].favorite,
                    (item[1].name.strip() or f"Сайт {item[0] + 1}").lower(),
                    item[0],
                )
            )

        for zero_based_index, site in indexed_sites:
            index = zero_based_index + 1
            name = site.name.strip() or f"Сайт {index}"
            category = site.category.strip()
            if selected_category and category != selected_category:
                continue

            search_blob = " ".join([name, category, site.base_url.strip(), site.manager_url.strip()]).lower()
            if search_query and search_query not in search_blob:
                continue

            self.filtered_site_indices.append(zero_based_index)
            display_name = f"[{category}] {name}" if category else name
            if site.favorite:
                display_name = f"★ {display_name}"
            self.site_list.addItem(display_name)

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

    def load_site_into_form(self, site: Site | None) -> None:
        self.is_loading_site = True
        self.clear_path_inputs()

        if site is None:
            self.site_name_input.setText("")
            self.category_input.setText("")
            self.base_url_input.setText("")
            self.manager_url_input.setText("")
            self.favorite_checkbox.setChecked(False)
            self.add_path_input(save_after=False)
            self.is_loading_site = False
            return

        self.site_name_input.setText(site.name)
        self.category_input.setText(site.category)
        self.base_url_input.setText(site.base_url)
        self.manager_url_input.setText(site.manager_url)
        self.favorite_checkbox.setChecked(site.favorite)

        if site.paths:
            for path in site.paths:
                self.add_path_input(path, save_after=False)
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

        status_label = QLabel("Не проверено")
        status_label.setMinimumWidth(120)
        field.textChanged.connect(lambda _text, label=status_label: self.reset_status_label(label))
        row_layout.addWidget(field)
        row_layout.addWidget(status_label)

        remove_button = QPushButton("x")
        remove_button.setFixedWidth(32)
        remove_button.clicked.connect(lambda _checked=False, widget=row_widget: self.remove_path_input(widget))
        row_layout.addWidget(remove_button)

        self.path_rows.append((row_widget, field, status_label))
        self.paths_layout.addWidget(row_widget)

        if save_after:
            self.save_current_site()

    def remove_path_input(self, row_widget: QWidget) -> None:
        if len(self.path_rows) == 1:
            self.path_rows[0][1].clear()
            self.save_current_site()
            return

        for index, (widget, _field, _status_label) in enumerate(self.path_rows):
            if widget is row_widget:
                self.path_rows.pop(index)
                self.paths_layout.removeWidget(widget)
                widget.deleteLater()
                break

        self.save_current_site()

    def clear_path_inputs(self) -> None:
        while self.path_rows:
            row_widget, _field, _status_label = self.path_rows.pop()
            self.paths_layout.removeWidget(row_widget)
            row_widget.deleteLater()

    def bulk_add_paths(self) -> None:
        if self.current_site_index < 0 or self.current_site_index >= len(self.sites):
            QMessageBox.warning(self, "Ошибка", "Выберите сайт.")
            return

        raw_paths, accepted = QInputDialog.getMultiLineText(
            self,
            "Массовое добавление path",
            "Вставьте path по одному на строку:",
        )
        if not accepted:
            return

        new_paths = [line.strip() for line in raw_paths.splitlines() if line.strip()]
        if not new_paths:
            QMessageBox.information(self, "Массовое добавление path", "Нет path для добавления.")
            return

        existing_paths = [field.text().strip() for _widget, field, _status_label in self.path_rows if field.text().strip()]
        merged_paths: list[str] = []
        for path in [*existing_paths, *new_paths]:
            if path not in merged_paths:
                merged_paths.append(path)

        self.clear_path_inputs()
        for path in merged_paths:
            self.add_path_input(path, save_after=False)
        if not merged_paths:
            self.add_path_input(save_after=False)

        self.save_current_site()
        QMessageBox.information(
            self,
            "Массовое добавление path",
            f"Добавлено path: {len(merged_paths) - len(existing_paths)}",
        )

    def add_common_path_input(self, value: str = "", save_after: bool = True) -> None:
        row_widget = QWidget()
        container_layout = QVBoxLayout(row_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        field = QLineEdit()
        field.setPlaceholderText("/page или section/item")
        field.setText(value)
        field.textChanged.connect(self.save_state)

        status_label = QLabel("Не проверено")
        status_label.setMinimumWidth(120)
        field.textChanged.connect(lambda _text, label=status_label: self.reset_status_label(label))
        row_layout.addWidget(field)
        row_layout.addWidget(status_label)

        details_button = QPushButton("Детали")
        details_button.setVisible(False)
        details_button.setCheckable(True)
        row_layout.addWidget(details_button)

        remove_button = QPushButton("x")
        remove_button.setFixedWidth(32)
        remove_button.clicked.connect(lambda _checked=False, widget=row_widget: self.remove_common_path_input(widget))
        row_layout.addWidget(remove_button)

        details_label = QLabel("")
        details_label.setWordWrap(True)
        details_label.setVisible(False)
        details_label.setStyleSheet("color: #505050; padding-left: 4px;")
        details_label.setTextFormat(Qt.TextFormat.RichText)
        details_button.toggled.connect(details_label.setVisible)
        field.textChanged.connect(
            lambda _text, button=details_button, label=details_label: self.reset_common_path_details(button, label)
        )

        container_layout.addLayout(row_layout)
        container_layout.addWidget(details_label)

        self.common_path_rows.append((row_widget, field, status_label, details_button, details_label))
        self.common_paths_layout.addWidget(row_widget)

        if save_after:
            self.save_state()

    def remove_common_path_input(self, row_widget: QWidget) -> None:
        if len(self.common_path_rows) == 1:
            self.common_path_rows[0][1].clear()
            self.save_state()
            return

        for index, (widget, _field, _status_label, _details_button, _details_label) in enumerate(self.common_path_rows):
            if widget is row_widget:
                self.common_path_rows.pop(index)
                self.common_paths_layout.removeWidget(widget)
                widget.deleteLater()
                break

        self.save_state()

    def clear_common_path_inputs(self) -> None:
        while self.common_path_rows:
            row_widget, _field, _status_label, _details_button, _details_label = self.common_path_rows.pop()
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
        return [
            field.text().strip()
            for _widget, field, _status_label, _details_button, _details_label in self.common_path_rows
            if field.text().strip()
        ]

    def bulk_add_common_paths(self) -> None:
        raw_paths, accepted = QInputDialog.getMultiLineText(
            self,
            "Массовое добавление общего path",
            "Вставьте path по одному на строку:",
        )
        if not accepted:
            return

        new_paths = [line.strip() for line in raw_paths.splitlines() if line.strip()]
        if not new_paths:
            QMessageBox.information(self, "Массовое добавление общего path", "Нет path для добавления.")
            return

        existing_paths = self.collect_common_paths()
        merged_paths: list[str] = []
        for path in [*existing_paths, *new_paths]:
            if path not in merged_paths:
                merged_paths.append(path)

        self.clear_common_path_inputs()
        for path in merged_paths:
            self.add_common_path_input(path, save_after=False)
        if not merged_paths:
            self.add_common_path_input(save_after=False)

        self.save_state()
        QMessageBox.information(
            self,
            "Массовое добавление общего path",
            f"Добавлено path: {len(merged_paths) - len(existing_paths)}",
        )

    def collect_site_from_form(self) -> Site:
        return Site(
            name=self.site_name_input.text().strip(),
            category=self.category_input.text().strip(),
            base_url=self.base_url_input.text().strip(),
            manager_url=self.manager_url_input.text().strip(),
            paths=[field.text().strip() for _widget, field, _status_label in self.path_rows if field.text().strip()],
            favorite=self.favorite_checkbox.isChecked(),
        )

    def collect_state_from_form(self) -> AppState:
        self.state.common_paths = self.collect_common_paths()
        return self.state

    @staticmethod
    def should_refresh_site_list(previous_site: Site, updated_site: Site) -> bool:
        return (
            previous_site.name != updated_site.name
            or previous_site.category != updated_site.category
            or previous_site.base_url != updated_site.base_url
            or previous_site.manager_url != updated_site.manager_url
            or previous_site.favorite != updated_site.favorite
        )

    def save_current_site(self) -> None:
        if self.is_loading_site:
            return

        if self.current_site_index < 0 or self.current_site_index >= len(self.sites):
            return

        previous_site = self.sites[self.current_site_index]
        updated_site = self.collect_site_from_form()
        self.sites[self.current_site_index] = updated_site
        if self.should_refresh_site_list(previous_site, updated_site):
            self.refresh_site_list(preferred_site_index=self.current_site_index)
        self.save_state()

    def apply_state(self, state: AppState, persist: bool = False) -> None:
        self.state = state
        self.load_common_paths_into_form()
        self.refresh_site_list(preferred_site_index=0)
        if persist:
            self.save_state()

    def save_state(self) -> None:
        try:
            self.state_repository.save_state(self.collect_state_from_form())
        except OSError as error:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить JSON:\n{error}")

    def load_state(self) -> None:
        result = self.state_repository.load_state()
        self.apply_state(result.state, persist=False)
        if result.warning:
            QMessageBox.warning(self, "Ошибка", result.warning)

    def import_json(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт JSON",
            str(self.state_repository.state_file.parent),
            "JSON Files (*.json)",
        )
        if not file_name:
            return

        try:
            state = self.state_repository.load_json_file(file_name)
            self.apply_state(state, persist=True)
            QMessageBox.information(self, "Импорт", "База сайтов успешно импортирована.")
        except (OSError, ValueError, TypeError) as error:
            QMessageBox.warning(self, "Ошибка", f"Не удалось импортировать JSON:\n{error}")

    def export_json(self) -> None:
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт JSON",
            str(self.state_repository.state_file),
            "JSON Files (*.json)",
        )
        if not file_name:
            return

        try:
            self.state_repository.save_json_file(file_name, self.collect_state_from_form())
            QMessageBox.information(self, "Экспорт", "База сайтов успешно экспортирована.")
        except OSError as error:
            QMessageBox.warning(self, "Ошибка", f"Не удалось экспортировать JSON:\n{error}")

    def import_paths_from_site(self) -> None:
        if self.current_site_index < 0 or self.current_site_index >= len(self.sites):
            QMessageBox.warning(self, "Ошибка", "Выберите текущий сайт.")
            return

        current_category = self.sites[self.current_site_index].category.strip()
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
        source_paths = self.sites[source_index].paths
        current_paths = self.sites[self.current_site_index].paths

        merged_paths: list[str] = []
        for path in [*current_paths, *source_paths]:
            normalized_path = str(path).strip()
            if normalized_path and normalized_path not in merged_paths:
                merged_paths.append(normalized_path)

        self.sites[self.current_site_index].paths = merged_paths
        self.load_site_into_form(self.sites[self.current_site_index])
        self.save_current_site()
        QMessageBox.information(self, "Импорт path", "Path успешно импортированы.")

    def get_source_sites_for_paths(self, current_category: str) -> list[tuple[int, str]]:
        matching_sites = [
            (index, self.get_site_display_label(site, index))
            for index, site in enumerate(self.sites)
            if index != self.current_site_index and site.category.strip() == current_category and current_category
        ]
        if matching_sites:
            return matching_sites

        return [
            (index, self.get_site_display_label(site, index))
            for index, site in enumerate(self.sites)
            if index != self.current_site_index
        ]

    def get_site_display_label(self, site: Site, index: int) -> str:
        category = site.category.strip()
        name = site.name.strip() or f"Сайт {index + 1}"
        return f"{index + 1}. [{category}] {name}" if category else f"{index + 1}. {name}"

    def get_available_categories(self) -> list[str]:
        return sorted({site.category.strip() for site in self.sites if site.category.strip()}, key=str.lower)

    def get_matching_sites_by_category(self, category: str) -> list[Site]:
        return [
            site
            for site in self.sites
            if site.category.strip() == category and self.url_service.normalize_url(site.base_url)
        ]

    def prompt_for_category(self) -> str | None:
        categories = self.get_available_categories()
        if not categories:
            QMessageBox.warning(self, "Ошибка", "Нет категорий для выбора.")
            return None

        category, accepted = QInputDialog.getItem(
            self,
            "Выберите категорию",
            "Категория:",
            categories,
            0,
            False,
        )
        if not accepted or not category:
            return None
        return category

    @staticmethod
    def set_status_label(label: QLabel, text: str, color: str) -> None:
        label.setText(text)
        label.setStyleSheet(f"color: {color};")

    def reset_status_label(self, label: QLabel) -> None:
        self.set_status_label(label, "Не проверено", "#808080")

    @staticmethod
    def reset_common_path_details(button: QPushButton, label: QLabel) -> None:
        button.setChecked(False)
        button.setVisible(False)
        label.clear()
        label.setVisible(False)

    def has_active_checks(self) -> bool:
        return self.site_check_thread is not None or self.common_check_thread is not None

    def set_site_check_running(self, is_running: bool) -> None:
        self.left_panel.setEnabled(not is_running)
        self.base_url_input.setEnabled(not is_running)
        self.paths_container.setEnabled(not is_running)
        self.add_path_button.setEnabled(not is_running)
        self.check_paths_button.setEnabled(not is_running)

    def set_common_check_running(self, is_running: bool) -> None:
        self.left_panel.setEnabled(not is_running)
        self.common_paths_container.setEnabled(not is_running)
        self.add_common_path_button.setEnabled(not is_running)
        self.check_common_paths_button.setEnabled(not is_running)

    def update_site_path_status(self, row_index: int, status_text: str, color: str) -> None:
        if 0 <= row_index < len(self.path_rows):
            self.set_status_label(self.path_rows[row_index][2], status_text, color)

    def finish_site_path_check(self) -> None:
        self.set_site_check_running(False)
        self.site_check_thread = None
        self.site_check_worker = None

    def update_common_path_status(self, row_index: int, status_text: str, color: str, details_html: str) -> None:
        if 0 <= row_index < len(self.common_path_rows):
            _widget, _field, status_label, details_button, details_label = self.common_path_rows[row_index]
            self.set_status_label(status_label, status_text, color)
            details_label.setText(details_html)
            details_button.setChecked(False)
            details_button.setVisible(True)
            details_label.setVisible(False)

    def finish_common_path_check(self) -> None:
        self.set_common_check_running(False)
        self.common_check_thread = None
        self.common_check_worker = None

    def start_site_check(self, requests: Sequence[SitePathCheckRequest]) -> None:
        self.set_site_check_running(True)
        self.site_check_thread = QThread(self)
        self.site_check_worker = SitePathCheckWorker(requests, self.url_service.check_url_status)
        self.site_check_worker.moveToThread(self.site_check_thread)
        self.site_check_thread.started.connect(self.site_check_worker.run)
        self.site_check_worker.progress.connect(self.update_site_path_status)
        self.site_check_worker.finished.connect(self.site_check_thread.quit)
        self.site_check_worker.finished.connect(self.finish_site_path_check)
        self.site_check_worker.finished.connect(self.site_check_worker.deleteLater)
        self.site_check_thread.finished.connect(self.site_check_thread.deleteLater)
        self.site_check_thread.start()

    def start_common_path_check(self, requests: Sequence[CommonPathCheckRequest]) -> None:
        self.set_common_check_running(True)
        self.common_check_thread = QThread(self)
        self.common_check_worker = CommonPathCheckWorker(requests, self.url_service.check_url_status)
        self.common_check_worker.moveToThread(self.common_check_thread)
        self.common_check_thread.started.connect(self.common_check_worker.run)
        self.common_check_worker.progress.connect(self.update_common_path_status)
        self.common_check_worker.finished.connect(self.common_check_thread.quit)
        self.common_check_worker.finished.connect(self.finish_common_path_check)
        self.common_check_worker.finished.connect(self.common_check_worker.deleteLater)
        self.common_check_thread.finished.connect(self.common_check_thread.deleteLater)
        self.common_check_thread.start()

    def check_site_paths(self) -> None:
        if self.has_active_checks():
            QMessageBox.information(self, "Проверка path", "Дождитесь завершения текущей проверки.")
            return

        base_url = self.url_service.normalize_url(self.base_url_input.text())
        if not base_url:
            QMessageBox.warning(self, "Ошибка", "Введите основную ссылку.")
            return

        requests: list[SitePathCheckRequest] = []
        for row_index, (_widget, field, status_label) in enumerate(self.path_rows):
            path = field.text().strip()
            if not path:
                self.set_status_label(status_label, "Пусто", "#808080")
                continue

            self.set_status_label(status_label, "Проверка...", "#1f5aa6")
            requests.append(
                SitePathCheckRequest(
                    row_index=row_index,
                    url=self.url_service.build_url(base_url, path),
                )
            )

        if not requests:
            QMessageBox.information(self, "Проверка path", "Нет заполненных path для проверки.")
            return

        self.start_site_check(requests)

    def check_common_paths_by_category(self) -> None:
        if self.has_active_checks():
            QMessageBox.information(self, "Проверка общего path", "Дождитесь завершения текущей проверки.")
            return

        category = self.prompt_for_category()
        if not category:
            return

        paths = self.collect_common_paths()
        if not paths:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы один общий path.")
            return

        matching_sites = self.get_matching_sites_by_category(category)
        if not matching_sites:
            QMessageBox.warning(self, "Ошибка", "В этой категории нет сайтов с основной ссылкой.")
            return

        requests: list[CommonPathCheckRequest] = []
        for row_index, (_widget, field, status_label, details_button, details_label) in enumerate(self.common_path_rows):
            path = field.text().strip()
            if not path:
                self.set_status_label(status_label, "Пусто", "#808080")
                self.reset_common_path_details(details_button, details_label)
                continue

            self.set_status_label(status_label, "Проверка...", "#1f5aa6")
            self.reset_common_path_details(details_button, details_label)
            requests.append(
                CommonPathCheckRequest(
                    row_index=row_index,
                    site_requests=[
                        CommonPathSiteRequest(
                            site_name=site.name.strip() or "Без названия",
                            url=self.url_service.build_url(site.base_url, path),
                        )
                        for site in matching_sites
                    ],
                )
            )

        if not requests:
            QMessageBox.information(self, "Проверка общего path", "Нет заполненных общих path для проверки.")
            return

        self.start_common_path_check(requests)

    def open_url(self, url: str, error_message: str) -> None:
        target = self.url_service.normalize_url(url)
        if not target:
            QMessageBox.warning(self, "Ошибка", error_message)
            return

        try:
            self.url_service.open_in_browser(target)
        except Exception as error:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть браузер:\n{error}")

    def open_site(self) -> None:
        self.open_url(self.base_url_input.text(), "Введите основную ссылку.")

    def open_manager(self) -> None:
        manager_url = self.manager_url_input.text().strip()
        if not manager_url:
            base_url = self.base_url_input.text().strip()
            manager_url = self.url_service.build_url(base_url, "manager/") if base_url else ""

        self.open_url(manager_url, "Введите Manager URL или основную ссылку.")

    def open_paths(self) -> None:
        base_url = self.url_service.normalize_url(self.base_url_input.text())
        if not base_url:
            QMessageBox.warning(self, "Ошибка", "Введите основную ссылку.")
            return

        paths = [field.text().strip() for _widget, field, _status_label in self.path_rows if field.text().strip()]
        if not paths:
            self.open_url(base_url, "Введите основную ссылку.")
            return

        for path in paths:
            self.open_url(self.url_service.build_url(base_url, path), "Не удалось открыть path.")

    def open_category_path(self) -> None:
        category = self.prompt_for_category()
        if not category:
            return

        paths = self.collect_common_paths()
        if not paths:
            QMessageBox.warning(self, "Ошибка", "Добавьте хотя бы один общий path.")
            return

        matching_sites = self.get_matching_sites_by_category(category)
        if not matching_sites:
            QMessageBox.warning(self, "Ошибка", "В этой категории нет сайтов с основной ссылкой.")
            return

        for site in matching_sites:
            for path in paths:
                self.open_url(self.url_service.build_url(site.base_url, path), "Не удалось открыть общий path.")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.has_active_checks():
            QMessageBox.information(self, "Проверка", "Дождитесь завершения текущей проверки перед закрытием окна.")
            event.ignore()
            return
        super().closeEvent(event)
