from _bootstrap import add_repo_root_to_sys_path

add_repo_root_to_sys_path()

from tests.harness.oktav_dataset.og_export import og_export_main


if __name__ == "__main__":
    raise SystemExit(og_export_main())
