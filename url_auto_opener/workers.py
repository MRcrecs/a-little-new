from html import escape
from typing import Callable, Sequence

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from .models import CommonPathCheckRequest, SitePathCheckRequest, UrlStatus


class SitePathCheckWorker(QObject):
    progress = pyqtSignal(int, str, str)
    finished = pyqtSignal()

    def __init__(
        self,
        requests: Sequence[SitePathCheckRequest],
        check_url_status: Callable[[str], UrlStatus],
    ) -> None:
        super().__init__()
        self.requests = list(requests)
        self.check_url_status = check_url_status

    @pyqtSlot()
    def run(self) -> None:
        for request in self.requests:
            status = self.check_url_status(request.url)
            self.progress.emit(request.row_index, status.text, status.color)
        self.finished.emit()


class CommonPathCheckWorker(QObject):
    progress = pyqtSignal(int, str, str, str)
    finished = pyqtSignal()

    def __init__(
        self,
        requests: Sequence[CommonPathCheckRequest],
        check_url_status: Callable[[str], UrlStatus],
    ) -> None:
        super().__init__()
        self.requests = list(requests)
        self.check_url_status = check_url_status

    @pyqtSlot()
    def run(self) -> None:
        for request in self.requests:
            total_sites = len(request.site_requests)
            success_count = 0
            redirect_count = 0
            site_status_lines: list[str] = []

            for site_request in request.site_requests:
                status = self.check_url_status(site_request.url)
                site_status_lines.append(
                    f"<div><span style='color:{status.color}; font-weight:600;'>{escape(site_request.site_name)}</span>"
                    f"<span style='color:{status.color};'>: {escape(status.text)}</span></div>"
                )
                if status.kind == "success":
                    success_count += 1
                elif status.kind == "redirect":
                    redirect_count += 1

            if success_count == total_sites:
                summary_color = "#228b22"
            elif success_count or redirect_count:
                summary_color = "#b8860b"
            else:
                summary_color = "#b22222"

            summary_text = f"{success_count}/{total_sites} OK"
            if redirect_count:
                summary_text += f", {redirect_count} redirect"

            self.progress.emit(request.row_index, summary_text, summary_color, "".join(site_status_lines))

        self.finished.emit()
