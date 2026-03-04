from dataclasses import dataclass, field
from typing import Literal


StatusKind = Literal["success", "redirect", "error"]


@dataclass(slots=True)
class Site:
    name: str
    category: str = ""
    base_url: str = ""
    manager_url: str = ""
    paths: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AppState:
    sites: list[Site] = field(default_factory=list)
    common_paths: list[str] = field(default_factory=list)


@dataclass(slots=True)
class LoadStateResult:
    state: AppState
    warning: str | None = None


@dataclass(slots=True, frozen=True)
class UrlStatus:
    text: str
    color: str
    kind: StatusKind


@dataclass(slots=True, frozen=True)
class SitePathCheckRequest:
    row_index: int
    url: str


@dataclass(slots=True, frozen=True)
class CommonPathSiteRequest:
    site_name: str
    url: str


@dataclass(slots=True, frozen=True)
class CommonPathCheckRequest:
    row_index: int
    site_requests: list[CommonPathSiteRequest]
