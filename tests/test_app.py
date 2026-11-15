import allure

from mmeln.app import add, farewell, greet, status, subtract


@allure.feature("Greeting module")
@allure.story("Default greeting")
def test_greet_default():
    # Act
    result = greet()
    # Assert
    assert result == "Hello, World!"


@allure.feature("Greeting module")
@allure.story("Personalized greeting")
def test_greet_custom_name():
    # Arrange
    user_name = "Marharyta"
    # Act
    result = greet(user_name)
    # Assert
    assert result == "Hello, Marharyta!"


@allure.feature("Farewell module")
@allure.story("Personalized farewell")
def test_farewell():
    # Arrange
    user_name = "KPI"
    # Act
    result = farewell(user_name)
    # Assert
    assert result == "Goodbye, KPI!"


@allure.feature("System module")
@allure.story("Health status check")
def test_status():
    # Act
    result = status()
    # Assert
    assert result == "OK"


@allure.feature("Math module")
@allure.story("Addition")
def test_add():
    # Arrange & Act
    result = add(2, 3)
    # Assert
    assert result == 5


@allure.feature("Math module")
@allure.story("Subtraction")
def test_subtract():
    # Arrange & Act
    result = subtract(10, 4)
    # Assert
    assert result == 6
