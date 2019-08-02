import asyncio
from unittest.mock import MagicMock

class IterMock:
    def __init__(self, obj):
        self._it = iter(obj)

    async def __anext__(self):
        try:
            value = next(self._it)
        except StopIteration:
            raise StopAsyncIteration
        return value

class AsyncForMock(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tests = kwargs.get('tests')

    def __aiter__(self):
        return IterMock(self.tests)

def AsyncMock(*args, **kwargs):
    mock = MagicMock(*args, **kwargs)

    async def async_mock(*args, **kwargs):
        return mock(*args, **kwargs)

    async_mock.mock = mock
    return async_mock
