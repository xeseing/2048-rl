"""The package is installed and importable.

Not a game test — there is no game yet. This fails if the packaging in
pyproject.toml is wrong, which is the only thing TASK-01 builds.
"""

import game2048


def test_package_is_importable_and_versioned():
    assert game2048.__version__
