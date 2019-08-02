from marshmallow_annotations import registry
from marshmallow_annotations.ext.attrs import AttrsSchema
from marshmallow import fields, Schema
try:
    from . import model
except ImportError:
    import model.model
from bson import ObjectId

registry.register_field_for_type(ObjectId, fields.String)


class TestSchema(Schema):
    field1 = fields.String()
    field2 = fields.String()
    field3 = fields.String()


class DateSchema(AttrsSchema):
    class Meta:
        target = model.Date
        register_as_scheme = True


class ChildFieldSchema(AttrsSchema):
    class Meta:
        target = model.ChildField
        register_as_scheme = True

        class Fields:
            id = {"dump_to": '_id', 'load_from': '_id'}


class DocumentSchema(AttrsSchema):
    class Meta:
        target = model.Document
        register_as_scheme = True

        class Fields:
            id = {"dump_to": '_id', 'load_from': '_id'}


ChildField = ChildFieldSchema()
ChildFields = ChildFieldSchema(many=True)
Date = DateSchema()
Dates = DateSchema(many=True)
Document = DocumentSchema()
Documents = DocumentSchema(many=True)


__all__ = [
    'ChildField',
    'ChildFields',
    'ChildFieldSchema',
    'Date',
    'Dates',
    'DateSchema',
    'Document',
    'Documents',
    'DocumentSchema'
]
