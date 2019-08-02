import unittest
from unittest.mock import MagicMock, patch

from hypothesis import given
import hypothesis.strategies as st
# from . import strategies

try:
    from tests.async_mock import AsyncMock
except(ModuleNotFoundError):
    from model.tests.async_mock import AsyncMock

try:
    import repo
except(ModuleNotFoundError):
    from model import repo

from model import model

try:
    import schema
except(ModuleNotFoundError):
    from model import schema

from typing import *
from attr import attrs, attrib, Factory
import asyncio


@attrs(slots=True, auto_attribs=True)
class MockCollection:
    data: List[Any]
    find_one_and_update_response: Optional[Any]

    async def find(self, criteria={}):
        for d in self.data:
            yield d

    async def find_one_and_update(self, id, update, upsert):
        return self.find_one_and_update_response


class TestDocumentRepo(unittest.TestCase):
    @given(st.lists(st.from_type(model.Document)))
    def test_find(self, documents):
        self.maxDiff = None
        _documents = [ c.to_bson() for c in documents ]

        async def run_test():
            collection = MockCollection(_documents, None)
            document_repo = repo.DocumentRepo(collection=collection)

            self.assertEqual(document_repo.collection, collection)

            results = []
            async for item in document_repo.find():
                results.append(item)

            for result, expected in zip(results, documents):
                if result != expected:
                    print(result, expected)
                self.assertEqual(result, expected)

        asyncio.get_event_loop().run_until_complete(run_test())
