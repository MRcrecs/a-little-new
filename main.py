import json
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urljoin

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("URL Auto Opener")
        self.resize(720, 480)

        self.state_file = self.get_state_file_path()
        self.path_inputs: list[QLineEdit] = []

        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        main_layout.addWidget(QLabel("Основная ссылка"))

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("https://example.com/")
        self.base_url_input.textChanged.connect(self.save_state)
        main_layout.addWidget(self.base_url_input)

        actions_layout = QHBoxLayout()

        import_button = QPushButton("Импорт JSON")
        import_button.clicked.connect(self.import_json)
        actions_layout.addWidget(import_button)

        export_button = QPushButton("Экспорт JSON")
        export_button.clicked.connect(self.export_json)
        actions_layout.addWidget(export_button)

        save_button = QPushButton("Сохранить JSON")
        save_button.clicked.connect(self.save_state)
        actions_layout.addWidget(save_button)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        paths_header = QHBoxLayout()
        paths_header.addWidget(QLabel("Path"))
        paths_header.addStretch()

        add_button = QPushButton("+")
        add_button.setFixedWidth(40)
        add_button.clicked.connect(lambda: self.add_path_input())
        paths_header.addWidget(add_button)
        main_layout.addLayout(paths_header)

        self.paths_container = QWidget()
        self.paths_layout = QVBoxLayout(self.paths_container)
        self.paths_layout.setContentsMargins(0, 0, 0, 0)
        self.paths_layout.setSpacing(10)
        self.paths_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setWidget(self.paths_container)
        main_layout.addWidget(scroll)

        open_button = QPushButton("Открыть вместе с path")
        open_button.setMinimumHeight(42)
        open_button.clicked.connect(self.open_urls)
        main_layout.addWidget(open_button)

        self.load_state()

    @staticmethod
    def get_state_file_path() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).with_name("urls.json")
        return Path(__file__).with_name("urls.json")

    def add_path_input(self, value: str = "") -> None:
        field = QLineEdit()
        field.setPlaceholderText("/page или section/item")
        field.setText(value)
        field.textChanged.connect(self.save_state)
        self.path_inputs.append(field)
        self.paths_layout.addWidget(field)
        self.save_state()

    def clear_path_inputs(self) -> None:
        while self.path_inputs:
            field = self.path_inputs.pop()
            self.paths_layout.removeWidget(field)
            field.deleteLater()

    def collect_data(self) -> dict:
        return {
            "main_url": self.base_url_input.text().strip(),
            "paths": [field.text().strip() for field in self.path_inputs if field.text().strip()],
        }

    def apply_data(self, data: dict) -> None:
        main_url = str(data.get("main_url", "")).strip()
        paths = data.get("paths", [])
        if not isinstance(paths, list):
            raise ValueError("Поле 'paths' должно быть списком.")

        normalized_paths = [str(path).strip() for path in paths if str(path).strip()]

        self.base_url_input.blockSignals(True)
        self.base_url_input.setText(main_url)
        self.base_url_input.blockSignals(False)

        self.clear_path_inputs()
        if normalized_paths:
            for path in normalized_paths:
                self.add_path_input(path)
        else:
            self.add_path_input()

        self.save_state()

    def save_json_file(self, file_path: Path) -> None:
        file_path.write_text(
            json.dumps(self.collect_data(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_json_file(self, file_path: Path) -> None:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON должен содержать объект.")
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

        self.add_path_input()

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
            QMessageBox.information(self, "Импорт", "Данные успешно импортированы.")
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
            QMessageBox.information(self, "Экспорт", "Данные успешно экспортированы.")
        except OSError as error:
            QMessageBox.warning(self, "Ошибка", f"Не удалось экспортировать JSON:\n{error}")

    def open_urls(self) -> None:
        base_url = self.base_url_input.text().strip()
        if not base_url:
            QMessageBox.warning(self, "Ошибка", "Введите основную ссылку.")
            return

        paths = [field.text().strip() for field in self.path_inputs if field.text().strip()]
        urls = [base_url] if not paths else [urljoin(base_url.rstrip("/") + "/", path.lstrip("/")) for path in paths]

        self.save_state()

        for url in urls:
            webbrowser.open_new_tab(url)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
