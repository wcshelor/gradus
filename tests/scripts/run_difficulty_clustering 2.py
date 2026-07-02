from _bootstrap import add_repo_root_to_sys_path

add_repo_root_to_sys_path()

from tests.harness.difficulty_clustering.runner import main


if __name__ == "__main__":
    raise SystemExit(main())
