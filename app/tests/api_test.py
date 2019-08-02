"""
see https://docs.graphene-python.org/en/latest/testing/

"""

import app.gqlschema as gql
from graphene.test import Client
import unittest
import asyncio
from graphql.execution.executors.asyncio import AsyncioExecutor

from attr import attrs, attrib, Factory, fields
from model import model, schema
from model.repo import RepoError
from typing import *
from bson import ObjectId
from pymongo import ReturnDocument
from copy import deepcopy
from json import loads, dumps
from collections import OrderedDict
from hypothesis import given
import hypothesis.strategies as st



def to_dict(data):
    """
    This mostly exists to convert the ordered dicts which graphql spits out to non-ordered-dicts so they can be compared.
    """
    return loads(dumps(data)) 


@attrs(slots=True, auto_attribs=True)
class InMemoryDocumentRepo:
    data: List[model.Document] = Factory(list)

    def set_data(self, documents):
        for d in documents:
            self._save(d)

    def _find_by_id(self, document_id:str) -> Optional[model.Document]:
        for d in self.data:
            if d.id == document_id:
                return deepcopy(d)

    async def find_by_id(self, document_id:str) -> Optional[model.Document]:
        return self._find_by_id(document_id)

    async def find(self, criteria=None) -> Iterator[model.Document]:
        assert(criteria is None)
        for d in self.data:
            yield deepcopy(d)

    async def find_by_name(self, name:str):
        for document in self.data:
            if document.name == name:
               return deepcopy(document)

    async def create(self,
                     name:str,
                     age:Optional[int]=None,
                     archived:Optional[bool]=None,
                     child_field:Optional[List]=None) -> model.Document:
        if (await self.find_by_name(name)) is not None:
            raise RepoError({'name': ['already exists']})

        result = model.Document(
            name=name,
            age=age,
            archived=archived,
            child_field=child_field or [],
          )
        self.data.append(result)
        return result

    def _save(self, document:model.Document) -> model.Document:
        result = deepcopy(document)

        upserted = False

        if result.id is None:
            result.id = str(ObjectId())

        for i,c in enumerate(self.data):
            if c.id == result.id:
                self.data[i] = result
                upserted = True
                break
        
        if not upserted:
            self.data.append(result)

        return result

    async def save(self, document:model.Document) -> model.Document:
        return self._save(document)



class GQLTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.client = Client(gql.schema)
        self.document_repo = InMemoryDocumentRepo()
        gql.set_repos(_document_repo=self.document_repo)

    def tearDown(self):
        gql.set_repos(None)

    def execute(self, query):
        # execute query
        fut = gql.schema.execute(
            query,
            executor=AsyncioExecutor(),
            return_promise=True,
        )

        executed = asyncio.get_event_loop().run_until_complete(fut)

        return executed


class Document(GQLTest):

    DOCUMENTS_QUERY = """
    query{
      documents{
        id
        name
        age
        childField{
          name
          date{
            month
            year
          }
        }
      }
    }
    """

    def test_get_all_documents(self):
        #set up test data
        document = self.document_repo._save(
            model.Document(
                name="Anakin Skywalker",
                age=99,
                child_field=[
                    model.ChildField(
                        name="Luke Skywalker",
                        date=model.Date(month=8, year=2018)

                    )
                ]
            )
        )

        documents = [document]
        # self.document_repo.set_data(documents)

        result = self.execute(self.DOCUMENTS_QUERY)

        self.assertEqual(result.errors, None)

        self.assertEqual(to_dict(result.data), {
            'documents':[
                {
                    'id': d.id,
                    'name':d.name,
                    'age':d.age,
                    'childField':[
                        {
                            'name': "Luke Skywalker",
                            'date': {
                                'month': 8,
                                'year': 2018
                            }
                        }
                    ]
                } for d in documents
            ]
        })

    @given(st.from_type(model.Document))
    def test_get_document(self, document):
        document = self.document_repo._save(document)

        SINGLE_DOCUMENT_QUERY = """
        query {
            document(id:"%s") {
                id
                name
            }
        }
        """% document.id

        result = self.execute(SINGLE_DOCUMENT_QUERY)
        print('result', result.errors, to_dict(result.data))

        self.assertEqual(result.errors, None)
        self.assertEqual(to_dict(result.data), {'document':{ 'id': document.id, 'name':document.name }})

    CREATE_DOCUMENT_MUTATION = """
    mutation {
      createDocument(document:{
        name: "Anakin Skywalker"
        age: 30
      })
      {
      __typename
        ... on Document {
          name
          age
        }
        ... on Errors{
          errors{
            field
            messages
          }
        }
      }
    }
    """

    def test_create_document(self):
        self.document_repo.data = []

        result = self.execute(self.CREATE_DOCUMENT_MUTATION)
        self.maxDiff = 10012301230

        self.assertEqual(result.errors, None)
        self.assertEqual(to_dict(result.data), {
          'createDocument': {
            '__typename':"Document",
            'name':'Anakin Skywalker',
            'age':30,
          }
        })

    @given(st.from_type(model.Document))
    def test_set_document_archived(self, document):
        document = self.document_repo._save(document)

        SET_DOCUMENT_ARCHIVED_MUTATION = """
        mutation {
          setDocumentArchived(setArchived:{
            id: "%s"
            archived: true  
          })
          {
            __typename
              ... on Document {
                id
                name
                age
                archived
              }
            ... on Errors{
              errors{
                field
                messages
              }
            }
          }
        }
        """ % document.id

        documents = [document]

        self.document_repo.set_data(documents)

        result = self.execute(SET_DOCUMENT_ARCHIVED_MUTATION)

        self.assertEqual(result.errors, None)
        self.assertEqual(to_dict(result.data), {
          'setDocumentArchived':{
            '__typename': "Document",
            'id': document.id,
            'name':document.name,
            'age':document.age,
            'archived':True
          }
        })

    @given(st.from_type(model.Document))
    def test_add_child_field(self, document):
        document = self.document_repo._save(document)

        ADD_CHILD_FIELD_MUTATION = """
        mutation {
          addChildField(addChildField:{
            documentId: "%s"
            name: "Luke Skywalker"
            date: {
              month: 5,
              year: 2010
            }
          })
          {
            __typename
              ... on Document {
                id
                name
                age
                childField{
                  name
                  date{
                    month
                    year
                  }
                }
              }
              ... on Errors{
                errors{
                  field
                  messages
                }
              }
            }
          }
        """ % document.id

        # self.customer_repo.set_data([customer])
        result = self.execute(ADD_CHILD_FIELD_MUTATION)
        self.assertEqual(result.errors, None)
        self.assertEqual(to_dict(result.data), {
          'addChildField':{
            '__typename': 'Document',
            'id': document.id,
            'name':document.name,
            'age':document.age,
            'childField': [
              {
                  'name':'Luke Skywalker',
                  'date': {'month':5, 'year':2010}
              }
            ]
          }
        })

    def test_remove_child_field(self):
        document = self.document_repo._save(
            model.Document(
                name="Anakin Skywalker",
                age=99,
                child_field=[
                    model.ChildField(
                        name="Luke Skywalker",
                        date=model.Date(month=8, year=2018)

                    )
                ]
            )
        )

        self.document_repo.set_data([document])

        REMOVE_CHILD_FIELD_MUTATION = """
        mutation {
          removeChildField(removeChildField:{
            documentId: "%s"
            childFieldId: "%s"
          })
          {
            __typename
              ... on Document {
                id
                name
                age
                childField{
                  name
                  date{
                    month
                    year
                  }
                }
              }
              ... on Errors{
                errors{
                  field
                  messages
                }
              }
            }
        } 
        """ % (document.id, document.child_field[0].id)

        result = self.execute(REMOVE_CHILD_FIELD_MUTATION)
        self.assertEqual(result.errors, None)
        data = to_dict(result.data)['removeChildField']
        print (data)
        child_fields = data['childField']
        child_fields_ids = [a['id'] for a in child_fields]
        self.assertTrue(document.child_field[0].id not in child_fields_ids)

    def test_edit_child_field(self):
        document = self.document_repo._save(
            model.Document(
                name="Anakin Skywalker",
                age=99,
                child_field=[
                    model.ChildField(
                        name="Luke Skywalker",
                        date=model.Date(month=8, year=2018)

                    )
                ]
            )
        )

        self.document_repo.set_data([document])

        EDIT_CHILD_FIELD_MUTATION = """
        mutation {
          editChildField(editChildField:{
            documentId: "%s"
            childField:{
              id: "%s"
              name: "Yoda"
              date: {
                month: 5,
                year: 2010
              }
            }
          })
          {
          __typename
            ... on Document {
              id
              name
              age
              childField{
                name
                date{
                  month
                  year
                }
              }
            }
            ... on Errors{
              errors{
              field
              messages
              } 
            }
          }
        }
        
        """ % (document.id, document.child_field[0].id)

        result = self.execute(EDIT_CHILD_FIELD_MUTATION)
        self.assertEqual(result.errors, None)
        self.assertEqual(to_dict(result.data), {
            'editChildField': {
                '__typename': 'Document',
                'id': document.id,
                'name': document.name,
                'age': document.age,
                'childField': [
                    {
                        'name': 'Yoda',
                        'date': {'month': 5, 'year': 2010}
                    }
                ]
            }
        })


if __name__ == "__main__":
    unittest.main()