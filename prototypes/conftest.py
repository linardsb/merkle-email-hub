"""Stop pytest from collecting parked code under prototypes/.

These trees were moved out of `app/` because they are dormant. Their tests
import from their own (now-relocated) packages and would fail collection
against the production import paths. Treat the whole subtree as opaque to
pytest until the code is re-imported.
"""

from __future__ import annotations

collect_ignore_glob = ["**/*"]
