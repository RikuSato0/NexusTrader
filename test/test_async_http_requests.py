import pytest
from tradebot.base import AsyncHttpRequests

BASE_URL = "https://jsonplaceholder.typicode.com"

@pytest.mark.asyncio
async def test_get():
    url = f"{BASE_URL}/posts/1"
    code, result, error = await AsyncHttpRequests.get(url)

    assert code == 200
    assert result is not None
    assert isinstance(result, dict)
    assert 'id' in result
    assert error is None

@pytest.mark.asyncio
async def test_post():
    url = f"{BASE_URL}/posts"
    data = {
        'title': 'foo',
        'body': 'bar',
        'userId': 1
    }
    code, result, error = await AsyncHttpRequests.post(url, data=data)

    assert code == 201
    assert result is not None
    assert isinstance(result, dict)
    assert 'id' in result
    assert error is None

@pytest.mark.asyncio
async def test_put():
    url = f"{BASE_URL}/posts/1"
    data = {
        'id': 1,
        'title': 'foo',
        'body': 'bar',
        'userId': 1
    }
    code, result, error = await AsyncHttpRequests.put(url, data=data)

    assert code == 200
    assert result is not None
    assert isinstance(result, dict)
    assert result['id'] == 1
    assert error is None

@pytest.mark.asyncio
async def test_delete():
    url = f"{BASE_URL}/posts/1"
    code, result, error = await AsyncHttpRequests.delete(url)

    assert code == 200
    assert result == {}  # JSONPlaceholder returns an empty object for successful DELETE
    assert error is None

@pytest.mark.asyncio
async def test_error_response():
    url = f"{BASE_URL}/nonexistent"
    code, result, error = await AsyncHttpRequests.get(url)

    assert code == 404
    assert result is None
    assert error is not None

# Add this configuration to the AsyncHttpRequests class for testing
AsyncHttpRequests.config = {}
