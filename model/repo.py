from attr import attrs, attrib, Factory, fields

try:
    from .eventemitter import EventEmitter
except ImportError:
    from eventemitter import EventEmitter

# try:
#     import model
# except ImportError:
#     from model import model

try:
    from . import model
except ImportError:
    import model.model

try:
    from . import schema
except ImportError:
    import schema

from typing import *
from bson import ObjectId, Decimal128
from pymongo import ReturnDocument
import pymongo.errors
from bson.errors import InvalidId



def munge_object(v):
    """
    Convert a mongodb document to json-serializable data types.
    """
    if isinstance(v, dict):
        v = munge_dict(v)
    elif isinstance(v, list):
        v = munge_list(v)
    elif isinstance(v, ObjectId):
        v = str(v)
    elif isinstance(v, Decimal128):
        v = v.to_decimal()
    return v


def munge_list(items):
    """
    Munges a list of things from mongodb to make them json-serializable.
    """
    return [munge_object(item) for item in items]


def munge_dict(d):
    """
    Munges a dictionary of things from mongodb to make them json-serializable.
    """
    # convert a mongodb record to json for deserialization
    return {k:munge_object(v) for k,v in d.items()}


class RepoError(Exception):
    def __init__(self, errors:Dict[str,List[str]]):
        super(RepoError, self).__init__()
        self.errors = errors


@attrs(slots=True, auto_attribs=True)
class DocumentRepo(EventEmitter):
    collection: Any = Factory(lambda: None)

    def check_indices(self):
        """
        Confirm all the database indices are as they should be.
        """
        try:
            self.collection.create_index(
                [("name", pymongo.DESCENDING)],
                unique=True
            )
        except pymongo.errors.DuplicateKeyError as err:
            pass

    def _create_from_document(self, document):
        munged = munge_object(document)
        result, errors = schema.Document.load(munged)
        assert(not errors)
        return result

    async def find_by_id(self, id:str) -> Optional[model.Document]:
        """
        Can raise an InvalidId error if id is not a valid ObjectId
        """
        document = await self.collection.find_one({'_id':ObjectId(id)})
        return self._create_from_document(document) if document is not None else None

    async def find(self, criteria=None) -> Iterator[model.Document]:
        criteria = criteria or {}
        async for document in self.collection.find(criteria):
            yield self._create_from_document(document)

    async def create(self,
                     name:str,
                     age:Optional[int]=None,
                     archived:Optional[bool]=None,
                     child_field:Optional[List]=None) -> model.Document:
        document = model.Document(name=name, age=age, archived=archived, child_field=child_field or [])
        try:
            res = await self.collection.insert_one(document.to_bson())
        except pymongo.errors.DuplicateKeyError:
            raise RepoError({'name': ['already exists']})

        result = await self.find_by_id(str(res.inserted_id))
        self.emit("DocumentCreated", result)
        return result

    async def save(self, document:model.Document) -> None:
        data = document.to_bson()
        document = await self.collection.find_one_and_replace(
            {'_id':data.pop('_id')},
            data,
            return_document=ReturnDocument.AFTER
        )

        result = self._create_from_document(document)

        self.emit('DocumentSaved', result)

        return result



__all__ = [
    'RepoError',
    'InvalidId',
    'DocumentRepo'
]
