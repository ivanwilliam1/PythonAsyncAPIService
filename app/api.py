from sanic import Sanic
from sanic.response import json
from . import settings
from sanic_graphql import GraphQLView
from graphql.execution.executors.asyncio import AsyncioExecutor
import motor.motor_asyncio

from model.repo import *
from . import gqlschema as gql

app = Sanic(__name__)

@app.route("/")
async def test(request):
    return json({"hello": "world"})


@app.listener('before_server_start')
def init_graphql(app, loop):
    app.add_route(
        GraphQLView.as_view(
            schema=gql.schema,
            graphiql=True,
            enable_async=True,
            executor=AsyncioExecutor(loop=loop)
        ), 
        '/graphql'
    )


@app.listener('before_server_start')
async def init_repos(app, loop):
    """
    Make sure we instantiate repos with the correct collections after mongodb has connected.

    Make sure the repos are sent to the api for use in endpoints.
    """
    print(f'Connecting to mongodb: {settings.MONGODB_HOST!r}  {settings.MONGODB_PORT!r}')
    mongodb = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_HOST, settings.MONGODB_PORT)

    print(f'Connecting to database: {settings.MONGODB_DB_NAME!r}')
    db = mongodb[settings.MONGODB_DB_NAME]

    print(f'Mongodb collection: {settings.MONGODB_DB_COLLECTION_NAME!r}')
    mongodb_collection = db[settings.MONGODB_DB_COLLECTION_NAME]

    print('Creating repos')
    mongodb_repo = DocumentRepo(collection=mongodb_collection)

    mongodb_repo.check_indices()

    print('Repos:', mongodb_repo)
    gql.set_repos(_document_repo=mongodb_repo)


if __name__ == "__main__":
    app.run(host=settings.API_HOST, port=int(settings.API_PORT), debug=True)
