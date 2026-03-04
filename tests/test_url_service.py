import unittest

from url_auto_opener.url_service import UrlService


class UrlServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.url_service = UrlService()

    def test_normalize_url_adds_https_scheme(self) -> None:
        self.assertEqual(self.url_service.normalize_url("example.com"), "https://example.com")

    def test_build_url_joins_base_and_path(self) -> None:
        self.assertEqual(
            self.url_service.build_url("https://example.com/root/", "/catalog/item"),
            "https://example.com/root/catalog/item",
        )

    def test_status_from_code_marks_redirects_consistently(self) -> None:
        redirect_status = self.url_service.status_from_code(200, redirected=True)
        http_redirect_status = self.url_service.status_from_code(302)

        self.assertEqual(redirect_status.kind, "redirect")
        self.assertEqual(redirect_status.color, UrlService.REDIRECT_COLOR)
        self.assertEqual(http_redirect_status.kind, "redirect")

    def test_status_from_code_marks_errors(self) -> None:
        error_status = self.url_service.status_from_code(404)

        self.assertEqual(error_status.kind, "error")
        self.assertEqual(error_status.color, UrlService.ERROR_COLOR)


if __name__ == "__main__":
    unittest.main()
