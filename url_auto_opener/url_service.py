import webbrowser
from urllib import error, request
from urllib.parse import urljoin, urlparse

from .models import UrlStatus


class UrlService:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MODX-URL-Helper/1.0"
    SUCCESS_COLOR = "#228b22"
    REDIRECT_COLOR = "#b8860b"
    ERROR_COLOR = "#b22222"

    @staticmethod
    def normalize_url(url: str) -> str:
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

    @classmethod
    def status_from_code(cls, code: int, redirected: bool = False) -> UrlStatus:
        if redirected:
            return UrlStatus(
                text=f"{code} -> redirect",
                color=cls.REDIRECT_COLOR,
                kind="redirect",
            )
        if 200 <= code < 300:
            return UrlStatus(text=str(code), color=cls.SUCCESS_COLOR, kind="success")
        if 300 <= code < 400:
            return UrlStatus(text=str(code), color=cls.REDIRECT_COLOR, kind="redirect")
        return UrlStatus(text=str(code), color=cls.ERROR_COLOR, kind="error")

    @classmethod
    def no_response_status(cls) -> UrlStatus:
        return UrlStatus(text="Нет ответа", color=cls.ERROR_COLOR, kind="error")

    def check_url_status(self, url: str) -> UrlStatus:
        http_request = request.Request(url, headers={"User-Agent": self.USER_AGENT}, method="GET")

        try:
            with request.urlopen(http_request, timeout=8) as response:
                status = getattr(response, "status", 200)
                final_url = response.geturl()
                return self.status_from_code(status, redirected=final_url != url)
        except error.HTTPError as http_error:
            return self.status_from_code(http_error.code)
        except Exception:
            return self.no_response_status()

    @staticmethod
    def open_in_browser(url: str) -> None:
        try:
            browser = webbrowser.get()
            browser.open_new_tab(url)
        except webbrowser.Error:
            webbrowser.open_new_tab(url)
