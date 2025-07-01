class ValidationError(Exception):
    pass

class BaseModel:
    def __init__(self, **data):
        for k, v in data.items():
            setattr(self, k, v)
