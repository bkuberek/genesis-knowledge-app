from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="KNOWLEDGE",
    settings_files=["settings.toml"],
    environments=True,
    load_dotenv=True,
)
