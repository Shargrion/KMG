class OpenAIError(Exception):
    pass

class error:
    OpenAIError = OpenAIError

class Message:
    def __init__(self, content: str) -> None:
        self.content = content

class Choice:
    def __init__(self, content: str) -> None:
        self.message = Message(content)

class Completion:
    def __init__(self, content: str) -> None:
        self.choices = [Choice(content)]

class ChatCompletion:
    @staticmethod
    def create(*args, **kwargs):
        # Return an empty valid JSON object as string
        return Completion("{}")

api_key = ""
