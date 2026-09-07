from __future__ import annotations

from tests.scripts._bootstrap import add_repo_root_to_sys_path

add_repo_root_to_sys_path()

from tests.harness.cipi_dataset.python_analysis import main


if __name__ == "__main__":
    raise SystemExit(main())
