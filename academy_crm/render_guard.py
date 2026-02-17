"""
Safeguards to prevent this project from running on Render.com.

We deliberately detect Render's environment variables and, unless explicitly
overridden, crash the process during startup. This ensures that even if
Render still has access to the repository or tries to deploy the app, the
service will not start successfully.
"""

from __future__ import annotations

import logging
import os
from typing import Iterable

logger = logging.getLogger(__name__)


RENDER_ENV_KEYS: Iterable[str] = (
    "RENDER",
    "RENDER_SERVICE_ID",
    "RENDER_EXTERNAL_URL",
    "RENDER_GIT_BRANCH",
)


def is_running_on_render() -> bool:
    """
    Return True if the current process appears to be running on Render.com.

    Render sets several characteristic environment variables inside its
    containers. We do not rely on a single one in case Render changes
    behaviour slightly; if any known key is present we treat the environment
    as Render-managed.
    """
    return any(key in os.environ for key in RENDER_ENV_KEYS)


def enforce_not_running_on_render() -> None:
    """
    Prevent this project from running on Render by default.

    If the environment looks like Render and ALLOW_RENDER is not explicitly
    set to "true", this function raises RuntimeError during Django settings
    import, causing the process to exit and the deployment to fail.

    This is intentionally strict so that old Render services cannot keep
    running once this code is deployed there.
    """
    if not is_running_on_render():
        return

    allow_flag = os.getenv("ALLOW_RENDER", "").lower()
    if allow_flag == "true":
        logger.warning(
            "Render environment detected but ALLOW_RENDER=true is set; "
            "starting application anyway."
        )
        return

    # Hard fail: refuse to run on Render
    raise RuntimeError(
        "Render environment detected (environment variables such as RENDER/RENDER_SERVICE_ID "
        "are present). This project is configured to refuse running on Render.com. "
        "Remove Render deployment or set ALLOW_RENDER=true explicitly if you really "
        "intend to run it there."
    )

