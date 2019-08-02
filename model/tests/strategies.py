import hypothesis.strategies as st

# try:
#     import model.model
# except(ImportError):
from model import model

import datetime
import struct
import math
from string import printable
from bson import ObjectId 


def clamp(v, vmin, vmax):
    return max(min(v, vmax), vmin)


@st.composite
def object_id_strings(draw):
    """
    object_id_strings() -> None

    strategy to create random strings which are valid mongodb objectids
    """
    dt = draw(st.datetimes(min_value=datetime.datetime(2000, 1, 1), max_value=datetime.datetime(2100, 1, 1)))
    ts = clamp(int(dt.timestamp()), -2147483648 ,2147483647)

    t = struct.pack("i", ts)
    r = draw(st.binary(min_size=5, max_size=5))
    c = draw(st.binary(min_size=3, max_size=3))
    return str(ObjectId((t + r + c).hex()))



st.register_type_strategy(
    model.Date,
    st.builds(
        model.Date,
        st.integers(min_value=1,max_value=12), # month
        st.integers(min_value=2000, max_value=2100) # year
    )
)


st.register_type_strategy(
    model.ChildField,
    st.builds(
        model.ChildField,
        st.from_type(model.Date), # date
        st.text(alphabet=printable, max_size=160) # name
    )
)

st.register_type_strategy(
    model.Document,
    st.builds(
        model.Document,
        st.text(alphabet=printable, max_size=160), # name
        st.integers(min_value=1, max_value=100), # age
        st.booleans(), # archived
        st.lists(st.from_type(model.ChildField)), # child_field
        object_id_strings() # id
    )
)
