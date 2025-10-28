def init_sentry():
    from ..imports import Path, default_cfg, PluginPath, logger
    import sentry_sdk

    dsn_path_to_parse = Path(default_cfg.sentry.dsn_path) if default_cfg.sentry.dsn_path else None
    if dsn_path_to_parse and not dsn_path_to_parse.is_absolute():
        dsn_path = PluginPath.plugin_root / default_cfg.sentry.dsn_path
    elif dsn_path_to_parse is not None:
        dsn_path = dsn_path_to_parse
    else:
        dsn_path = None

    if dsn_path is None:
        logger.warning("Sentry DSN: (not set for empty path)")
        return
    
    if not dsn_path.is_file():
        logger.error(f"Sentry DSN: (not set, file {dsn_path} does not exist)")
        return
    
    try:
        dsn_str = dsn_path.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.error(f"Failed to read Sentry DSN from {dsn_path}: {e}")
        return
    
    if not dsn_str or dsn_str == "":
        logger.warning("Sentry DSN: (not set for empty content)")
        return

    logger.info(f"Sentry DSN: {dsn_str[:8] + '...' }")
    sentry_sdk.init(dsn=dsn_str, traces_sample_rate=1.0)
