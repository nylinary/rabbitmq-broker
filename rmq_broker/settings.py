import importlib

import environ

env = environ.Env()
settings_path = env("MICROSERVICE_SETTINGS", default="config.settings.base")

try:
    settings = importlib.import_module(settings_path)
except ModuleNotFoundError as e:
    raise AttributeError(
        "Specified microservice settings file path is not correct! Error: %s" % e
    )