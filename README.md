# Python Asynchronous API Service
#### PythonAsyncAPIService
## Description:
A GraphQL based API Service in Python for querying and mutating data in mongodb.

Technologies used:
1. Sanic (Web Framework)
2. AsyncIO
3. GraphQL

## Get Started

##### Clone repo.

`git clone https://github.com/ivanwilliam1/PythonAsyncAPIService.git`

##### Change to app directory.

`cd PythonAsyncAPIService/`

## Build Requirements

Python 3.4 (or greater) is required to be installed.

Notes: if you're running this in a development environment, create a venv and install the requirements there to make sure you have everything you need.

To install the requirements:

`pip install -r requirements.txt`

Alternately, there is a script which can be run with:

`./scripts/install-reqs.sh`

## Run

To run the server, run the following command from the main directory:

`python3 -m app.api`

Alternately, there is a script which can be run with:

`./scripts/run-api.sh`

The server provides a graphql api which can be used to administer the collections in mongodb.


## Docker build

To start a docker build, run

`docker build -t <image-name> .`

Here image-name should be replaced with the name you want, i.e.

`docker build -t python-async-api-service .`

## Docker run

To run things locally, you need a mongodb server:

`docker run --name  python-async-api-service-mongo -d mongo:4`

To run the container:

`docker run -p 8000:8000 <image-name>`

Here, image-name should be replace with the name you want, i.e.

`docker run -p 8000:8000 python-async-api-service`

## Unit Testing

This project uses pytest and hypothesis for unit tests.

To run the unit tests:

`python3 -m pytest app/tests`

Alternately, there is a script which can be run with:

`./scripts/run-tests.sh`

## Required Environment Variables

MONGODB_HOST defaults to 'localhost'

MONGODB_PORT defaults to mongodb's default port 27017

MONGODB_DB_NAME defaults to "TEST" and refers to the mongodb database name for the collection given below

MONGODB_DB_COLLECTION_NAME defaults to "Document" and should refer to the mongodb collection which will be used

ADMIN_API_HOST defaults to 0.0.0.0

ADMIN_API_PORT defaults to 8000

AUTO_RELOAD defaults to true


## Usage

This is the fun part. Here you get to experiment with the service.

### GET localhost:8000/
You can hit this default endpoint of the API. The following json will be returned:

{"hello":"world"}

The purpose of this endpoint is to have something for the devops/networks team to aussure the availibility of the service. 


### GET localhost:8000/graphql
This is the endpoint for the graphql playground. You can use this endpoint to experiment with the API using graphql

The sample graphql queries and mutations are available in `sample_graphql_queries/`. Use these sample commands to get started.

Likewise, you can click on the "Docs" link in the playground and explore the models for queries and mutations.
