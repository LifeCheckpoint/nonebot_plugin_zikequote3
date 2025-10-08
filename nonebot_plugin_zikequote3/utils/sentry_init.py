def init_sentry():
    from ..imports import Path, default_cfg, _plugin_root, logger
    import sentry_sdk

    dsn_path = Path(default_cfg.sentry.dsn_path) if default_cfg.sentry.dsn_path else None

    if dsn_path is None or not dsn_path.is_file():
        logger.info("Sentry DSN: (not set for empty path)")
        return
    
    try:
        dsn_str = (
            dsn_path if dsn_path.is_absolute() else (_plugin_root / dsn_path)
        ).read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.error(f"Failed to read Sentry DSN from {dsn_path}: {e}")
        return
    
    if dsn_str == "":
        logger.info("Sentry DSN: (not set for empty content)")
        return

    logger.info(f"Sentry DSN: {dsn_str[:8] + '...' }")
    sentry_sdk.init(dsn=dsn_str if dsn_str else None, send_default_pii=True)
