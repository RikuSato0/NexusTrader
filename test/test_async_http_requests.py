import pytest
from tradebot.base import AsyncHttpRequests

BASE_URL = "https://jsonplaceholder.typicode.com"

@pytest.mark.asyncio
async def test_get():
    url = f"{BASE_URL}/posts/1"
    result = await AsyncHttpRequests.get(url)

    assert isinstance(result, dict)
    assert 'id' in result

@pytest.mark.asyncio
async def test_post():
    url = f"{BASE_URL}/posts"
    data = {
        'title': 'foo',
        'body': 'bar',
        'userId': 1
    }
    result = await AsyncHttpRequests.post(url, json=data)

    assert isinstance(result, dict)
    assert 'id' in result

@pytest.mark.asyncio
async def test_put():
    url = f"{BASE_URL}/posts/1"
    data = {
        'id': 1,
        'title': 'foo',
        'body': 'bar',
        'userId': 1
    }
    result = await AsyncHttpRequests.put(url, json=data)

    assert isinstance(result, dict)
    assert result['id'] == 1

@pytest.mark.asyncio
async def test_delete():
    url = f"{BASE_URL}/posts/1"
    result = await AsyncHttpRequests.delete(url)

    assert isinstance(result, dict)
    assert result == {}  # JSONPlaceholder returns an empty object for successful DELETE

@pytest.mark.asyncio
async def test_error_response():
    url = f"{BASE_URL}/nonexistent"
    with pytest.raises(Exception) as exc_info:
        await AsyncHttpRequests.get(url)
    
    assert "404" in str(exc_info.value)

# Add this configuration to the AsyncHttpRequests class for testing
AsyncHttpRequests.config = {}
