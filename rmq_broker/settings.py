import importlib

import environ

env = environ.Env()
default_path = env("MICROSERVICE_SETTINGS", default="settings")
paths = [
    default_path,
    "config.settings.base",
    "app.settings",
    "settings",
    "application.settings",
]
settings = ""


for path in paths:
    try:
        settings = importlib.import_module(path)
    except ModuleNotFoundError:
        pass
    else:
        break

if settings == "":
    raise AttributeError(
        "Specified microservice settings file path is not correct! Error: %s"
        % default_path
    )
