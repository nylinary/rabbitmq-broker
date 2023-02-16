import importlib

import environ

env = environ.Env()
paths = {
    "Django": "config.settings.base",
    "FastAPI": "app.settings",
    }



try:
    settings_path = env("MICROSERVICE_SETTINGS", default=paths["Django"])
    settings = importlib.import_module(settings_path)
except ModuleNotFoundError as e:
    try:
        settings_path = env("MICROSERVICE_SETTINGS", default=paths["FastAPI"])
        settings = importlib.import_module(settings_path)
    except ModuleNotFoundError as e:
        raise AttributeError(
            "Specified microservice settings file path is not correct! Error: %s" % e
        )   