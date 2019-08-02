import graphene
from graphene.types.datetime import DateTime
from bson import ObjectId
import model.model as model
import model.repo as repo

document_repo = None

def set_repos(_document_repo=None):
    global document_repo
    print(f'gqlschema.set_repos: {_document_repo}')
    document_repo = _document_repo


class Date(graphene.ObjectType):
    month= graphene.Int()
    year= graphene.Int()

    @classmethod
    def from_model(cls, date):
        return cls(month=date.month, year=date.year)


class ChildField(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    date = graphene.Field(Date)

    @classmethod
    def from_model(cls, child_field):
        return cls(
            id=str(child_field.id),
            name = child_field.name,
            date = child_field.date
        )


class Document(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    age = graphene.Int()
    child_field = graphene.List(ChildField)
    archived = graphene.Boolean()

    @classmethod
    def from_model(cls, document):
        return cls(
            id=document.id,
            name=document.name,
            age=document.age,
            child_field=[ChildField.from_model(s) for s in document.child_field],
            archived=document.archived
        )


class Query(graphene.ObjectType):
    documents = graphene.List(Document)
    document = graphene.Field(Document, id=graphene.ID())

    async def resolve_documents(self, args, context=None, info=None):
        global document_repo
        assert(document_repo is not None)

        results = []
        async for document in document_repo.find():
            results.append(Document.from_model(document))
        return results

    async def resolve_document(self, args, id, context=None, info=None):
        global document_repo
        assert (document_repo is not None)

        try:
            document = await document_repo.find_by_id(id)
        except repo.InvalidId as exc:
            return Errors([Error('id',['invalid'])])

        if not document:
            return Errors([Error('id',['not found'])])

        result = Document.from_model(document)

        return result


class Error(graphene.ObjectType):
    field = graphene.String()
    messages = graphene.List(graphene.String)


class Errors(graphene.ObjectType):
    errors = graphene.List(Error)

    @classmethod
    def from_exception(cls, exc):
        return cls(errors=[Error(field=field,messages=messages) for field,messages in exc.errors.items()])


class DocumentResponse(graphene.Union):
    class Meta:
        types = (Document, Errors)


class CreateDocumentInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    age = graphene.Int(required=False)
    archived = graphene.String(required=False)


class CreateDocument(graphene.Mutation):
    class Arguments:
        document = CreateDocumentInput(required=True)

    Output = DocumentResponse

    async def mutate(self, info, document):
        global document_repo
        assert(document_repo is not None)

        try:
            result = await document_repo.create(name=document.name, age=document.age, archived=document.archived)
        except repo.RepoError as exc:
            return Errors.from_exception(exc)

        return Document.from_model(result)


class SetDocumentArchivedInput(graphene.InputObjectType):
    id = graphene.ID(required=True)
    archived = graphene.Boolean(required=True)


class SetDocumentArchived(graphene.Mutation):
    class Arguments:
        set_archived = SetDocumentArchivedInput(required=True)

    Output = DocumentResponse

    async def mutate(self, info, set_archived):
        global document_repo
        assert(document_repo is not None)

        try:
            document = await document_repo.find_by_id(set_archived.id)
        except repo.InvalidId as exc:
            return Errors([Error('id',['invalid'])])

        if not document:
            return Errors([Error('id',['not found'])])

        document.set_archived(set_archived.archived)
        result = await document_repo.save(document)
            
        return Document.from_model(result)


class DateInput(graphene.InputObjectType):
    month = graphene.Int(required=True)
    year = graphene.Int(required=True)

    def to_model(self):
        return model.Date(self.month, self.year)


class AddChildFieldInput(graphene.InputObjectType):
    document_id = graphene.ID(required=True)
    name = graphene.String()
    date = graphene.Field(DateInput, required=False)


class AddChildField(graphene.Mutation):
    class Arguments:
        add_child_field = AddChildFieldInput(required=True)

    Output = DocumentResponse

    async def mutate(self, info, add_child_field):
        global document_repo
        assert(document_repo is not None)

        try:
            document = await document_repo.find_by_id(add_child_field.document_id)
        except repo.InvalidId as exc:
            return Errors([Error('id',['invalid'])])

        if not document:
            return Errors([Error('id',['not found'])])

        document.add_child_field(
            model.ChildField(
                name=add_child_field.name,
                date=add_child_field.date.to_model(),
            )
        )

        result = await document_repo.save(document)

        return Document.from_model(result)


class RemoveChildFieldInput(graphene.InputObjectType):
    document_id = graphene.ID(required=True)
    child_field_id = graphene.ID(required=True)


class RemoveChildField(graphene.Mutation):
    class Arguments:
        remove_child_field = RemoveChildFieldInput(required=True)

    Output = DocumentResponse

    async def mutate(self, info, remove_child_field):
        global document_repo
        assert(document_repo is not None)

        try:
            document = await document_repo.find_by_id(remove_child_field.document_id)
        except repo.InvalidId as exc:
            return Errors([Error('id',['invalid'])])

        if not document:
            return Errors([Error('id',['not found'])])

        try:
            document.remove_child_field(remove_child_field.child_field_id)
        except KeyError as exc:
            return Errors([Error('contract_id',['not found'])])

        result = await document_repo.save(document)

        return Document.from_model(result)


class EditChildFieldInput(graphene.InputObjectType):
    id = graphene.ID(required=True)
    name = graphene.String()
    date = graphene.Field(DateInput, required=False)


class EditChildFieldMutationInput(graphene.InputObjectType):
    document_id = graphene.ID(required=True)
    child_field = graphene.InputField(EditChildFieldInput , description="Child field to update")


class EditChildField(graphene.Mutation):
    class Arguments:
        edit_child_field = EditChildFieldMutationInput(required=True)

    Output = DocumentResponse

    async def mutate(self, info, edit_child_field):
        global document_repo
        assert(document_repo is not None)

        try:
            document = await document_repo.find_by_id(edit_child_field.document_id)
        except repo.InvalidId as exc:
            return Errors([Error('id',['invalid'])])

        if not document:
            return Errors([Error('id',['not found'])])

        try:
            document.update_child_field(model.ChildField(
                id= edit_child_field.child_field.id,
                name=edit_child_field.child_field.name,
                date=edit_child_field.child_field.date.to_model()
            ))

        except KeyError as exc:
            return Errors([Error('contract_id', ['not found'])])

        result = await document_repo.save(document)

        return Document.from_model(result)



class Mutation(graphene.ObjectType):
    create_document = CreateDocument.Field()
    set_document_archived = SetDocumentArchived.Field()

    add_child_field = AddChildField.Field()
    remove_child_field = RemoveChildField.Field()
    edit_child_field = EditChildField.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)


__all__ = [
    'Date',
    'DateInput',
    'ChildField',
    'Document',
    'DocumentResponse',
    'SetDocumentArchived',
    'SetDocumentArchivedInput',
    'CreateDocument',
    'CreateDocumentInput',
    'AddChildField',
    'AddChildFieldInput',
    'EditChildField',
    'EditChildFieldInput',
    'EditChildFieldMutationInput',
    'RemoveChildField',
    'RemoveChildFieldInput',
    'Error',
    'Errors',
    'Query',
    'Mutation',
    'schema'
]

