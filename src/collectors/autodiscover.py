from __future__ import annotations

import importlib
import pkgutil
from typing import List


def autodiscover_collectors(packages: List[str] | None = None) -> None:
    """
    Imports all submodules under the given packages so @register decorators run.

    Default packages cover your structure:
      - collectors.google_jobs
      - collectors.discovery
      - collectors.ats
      - collectors.enterprise_ats
    """
    packages = packages or [
        "collectors.google_jobs",
        "collectors.discovery",
        "collectors.ats",
        "collectors.enterprise_ats",
    ]

    for pkg_name in packages:
        try:
            pkg = importlib.import_module(pkg_name)
        except ModuleNotFoundError:
            continue

        # walk all modules inside package and import them
        for m in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + "."):
            importlib.import_module(m.name)