import allure

from mmeln.app import farewell, greet


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
