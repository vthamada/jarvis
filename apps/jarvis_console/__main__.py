from apps.jarvis_console.bootstrap import ensure_src_paths

if __name__ == "__main__":
    ensure_src_paths()
    from apps.jarvis_console.cli import main

    raise SystemExit(main())
