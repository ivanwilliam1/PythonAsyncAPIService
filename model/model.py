from typing import *
from datetime import datetime
from attr import attrs, attrib, Factory
from bson import Decimal128, ObjectId
from bson.decimal128 import create_decimal128_context
import traceback


@attrs(slots=True, auto_attribs=True)
class Date:
    month: int
    year: int

    @classmethod
    def FromPeriod(cls, period):
        fmt = "%Y%m%d"
        d = datetime.strptime(period.split('-')[0], fmt)
        return cls(d.month, d.year)

    def __lt__(self, other):
        return self.year < other.year or (self.year == other.year and self.month < other.month)

    def __eq__(self, other):
        return self.year == other.year and self.month == other.month

    def __gt__(self, other):
        return self.year > other.year or (self.year == other.year and self.month > other.month)

    def to_bson(self):
        return {
            'month': self.month,
            'year': self.year
        }


@attrs(slots=True, auto_attribs=True)
class ChildField:
    date: Optional[Date]
    name: Optional[str] = Factory(lambda: None)
    id: str = Factory(lambda: str(ObjectId())) # unique id for the entry, used for deletions

    def to_bson(self):
        return {
            '_id': ObjectId(self.id),
            'name' : self.name,
            'date': None if self.date is None else self.date.to_bson()
        }


@attrs(slots=True, auto_attribs=True)
class Document:
    name: str
    age: Optional[int] = Factory(lambda: None)
    archived: Optional[bool] = Factory(lambda: False)
    child_field: List[ChildField] = Factory(list)
    id: Optional[str] = Factory(lambda: str(ObjectId()))

    def child_field_index(self, id:str):
        child_field_ids = [sub.id for sub in self.child_field]
        try:
            return child_field_ids.index(id)
        except ValueError:
            return None

    def find_child_field(self, id:str):
        index = self.child_field_index(id)
        if index is None:
            return None
        return self.child_field[index]

    def set_archived(self, value:bool) -> None:
        self.archived = value

    def add_child_field(self, child_field:ChildField):
        self.child_field.append(child_field)

    def remove_child_field(self, id:str) -> None:
        index = self.child_field_index(id)

        if index is None:
            raise KeyError("Could not find child field with id %s" % id)

        del self.child_field[index]

    def update_child_field(self, child_field:ChildField):
        index = self.child_field_index(child_field.id)

        if index is None:
            raise KeyError("Child field with the given index does not exist")

        self.child_field[index] = child_field

    def find_child_field_for_date(self, sub_date:Date) -> Optional[ChildField]:
        for sub in self.child_field:
            if sub.date == sub_date:
                return sub

    def to_bson(self):
        result = {
            "_id": ObjectId(self.id),
            "name": self.name,
            "age": self.age,
            "child_field": [s.to_bson() for s in self.child_field],
            "archived": self.archived
        }

        return result
