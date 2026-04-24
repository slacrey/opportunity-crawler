from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ResourceManifest:
    name: str
    source: Path
    target: str
    optional: bool = False


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def package_root() -> Path:
    return project_root() / "src" / "opportunity_crawler"


def default_config_templates_dir() -> Path:
    return project_root() / "packaging" / "defaults"


def migrations_dir() -> Path:
    return project_root() / "migrations" / "versions"


def frontend_dist_dir() -> Path:
    return project_root() / "frontend" / "dist"


def pyinstaller_hiddenimports() -> list[str]:
    return [
        "opportunity_crawler.shared.domain.rules",
        "opportunity_crawler.shared.domain.opportunity",
        "opportunity_crawler.shared.contracts.agent_protocol",
        "opportunity_crawler.control_plane.app",
        "opportunity_crawler.agent.app",
    ]


def resource_manifests() -> tuple[ResourceManifest, ...]:
    return (
        ResourceManifest(
            name="default_config_templates",
            source=default_config_templates_dir(),
            target="packaging/defaults",
        ),
        ResourceManifest(
            name="database_migrations",
            source=migrations_dir(),
            target="migrations/versions",
        ),
        ResourceManifest(
            name="frontend_static_assets",
            source=frontend_dist_dir(),
            target="frontend/dist",
            optional=True,
        ),
    )


def pyinstaller_datas() -> list[tuple[str, str]]:
    datas: list[tuple[str, str]] = []
    for resource in resource_manifests():
        if resource.source.exists():
            datas.append((str(resource.source), resource.target))
        elif not resource.optional:
            raise FileNotFoundError(f"required packaging resource missing: {resource.source}")
    return datas

