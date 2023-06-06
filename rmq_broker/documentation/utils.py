import inspect
import pathlib


def get_class_dir(chain) -> str:
    return pathlib.Path(inspect.getmodule(chain).__file__).parent.name
