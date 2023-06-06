class Singleton(object):
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls.__name__ not in cls._instances:
            cls._instances[cls.__name__] = super().__new__(cls, *args, **kwargs)
        return cls._instances[cls.__name__]
