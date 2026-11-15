def greet(name: str = "World") -> str:
    return f"Hello, {name}!"


def farewell(name: str) -> str:
    return f"Goodbye, {name}!"


def status() -> str:
    return "OK"


def add(a: int, b: int) -> int:
    return a + b


def subtract(a: int, b: int) -> int:
    return a - b


if __name__ == "__main__":
    print(greet())
