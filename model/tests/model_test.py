import unittest
from hypothesis import given, settings
import hypothesis.strategies as st
from . import strategies

from model import model

from bson import Decimal128, ObjectId
from bson.decimal128 import create_decimal128_context


class TestChildField(unittest.TestCase):
    @given(st.from_type(model.Date),
           st.text(alphabet=st.characters(whitelist_categories=('Nd',)), min_size=10, max_size=10))
    def test_constructor(self, date, name):
        result = model.ChildField(date, name)

        self.assertEqual(result.name, name)
        self.assertEqual(result.date, date)
        self.assertTrue(isinstance(result.id, str))

    @given(st.from_type(model.Date),
           st.text(alphabet=st.characters(whitelist_categories=('Nd',)), min_size=10, max_size=10))
    def test_to_bson(self, date, name):
        result = model.ChildField(date, name)

        bson = result.to_bson()

        self.assertEqual(result.name, bson['name'])
        self.assertEqual(result.date.to_bson(), bson['date'])
        self.assertEqual(ObjectId(result.id), bson['_id'])


class TestDocument(unittest.TestCase):
    @given(st.text(), st.integers())
    def test_default_constructor(self, name, age):
        document = model.Document(name, age)

        self.assertIsNotNone(document.id)
        self.assertEqual(document.name, name)
        self.assertEqual(document.age, age)
        self.assertEqual(document.archived, False)
        self.assertEqual(document.child_field, [])

    @given(st.text(), st.integers(), st.booleans(), st.lists(st.from_type(model.ChildField)) )
    def test_constructor(self, name, age, archived, child_field):
        document = model.Document(name, age, archived, child_field)

        self.assertIsNotNone(document.id)
        self.assertEqual(document.name, name)
        self.assertEqual(document.age, age)
        self.assertEqual(document.archived, archived)
        self.assertEqual(document.child_field, child_field)

    @given(st.from_type(model.Document))
    def test_to_bson(self, document):
        bson = document.to_bson()

        self.assertEqual(document.id, str(bson['_id']))
        self.assertEqual(document.name, bson['name'])
        self.assertEqual(document.age, bson['age'])
        self.assertEqual(document.archived, bson['archived'])
        self.assertEqual([s.to_bson() for s in document.child_field], bson['child_field'])

    @given(st.from_type(model.Document), st.from_type(model.ChildField))
    def test_add_remove_child_field(self, document, child_field):
        document.add_child_field(child_field)
        self.assertTrue(child_field in document.child_field)
        document.remove_child_field(child_field.id)
        self.assertFalse(child_field in document.child_field)

    @given(st.from_type(model.Document), st.from_type(model.ChildField), st.from_type(model.ChildField))
    def test_update_child_field(self, document, child_field, new_child_field):
        new_child_field.id = child_field.id
        document.add_child_field(child_field)
        document.update_child_field(new_child_field)
        self.assertEqual(document.find_child_field(child_field.id), new_child_field)
