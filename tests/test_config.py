from flowforge.core.config import Settings


def test_defaults_are_local_development_values(monkeypatch):
    for var in ("APP_ENV", "DEBUG", "LOG_LEVEL", "DATABASE_URL", "REDIS_URL"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(_env_file=None)
    assert settings.app_name == "FlowForge"
    assert settings.app_env == "local"
    assert settings.debug is False
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_environment_overrides_defaults(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("REDIS_URL", "redis://example:6380/2")
    settings = Settings(_env_file=None)
    assert settings.log_level == "DEBUG"
    assert settings.redis_url == "redis://example:6380/2"
