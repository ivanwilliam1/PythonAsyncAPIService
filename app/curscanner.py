from typing import *
import collections
import re
from datetime import datetime
import io
import boto3
import pymongo
import asyncio
import json
import traceback
import aio_pika
import motor.motor_asyncio

from awscommon import schema
from awscommon.model import *
from . import settings
from awscommon.repo import *


# TODO: everything except CUR_MANIFEST_PATTERN should come from environent variables
CUR_MANIFEST_PATTERN = re.compile('(?P<reportprefix>[^/]*)/(?P<reportname>[^/]*)/(?P<period>[^/]*)/(?P<reportname2>[^/]*)-Manifest.json') # pragma: no mutate


class S3ClientABC:
    """
    Abstract base class for the S3Client wrapper. Mostly used with MagicMock to automatical
    generate a mock S3Client.
    """
    __slots__ = ['role', 's3'] # pragma: no mutate
    
    role:Any
    s3: Any

    def __init__(self) -> None:
        super().__init__()
        self.role = None
        self.s3 = None

    def list_all_objects(self, bucket:str, prefix:str=None) -> Iterable[Dict[str,Any]]:
        raise NotImplementedError("S3ClientABC is an ABC")

    def download(self, bucket:str, key:str) -> io.BytesIO:
        raise NotImplementedError("S3ClientABC is an ABC")

    def download_json(self, bucket:str, key:str) -> Any:
        raise NotImplementedError("S3ClientABC is an ABC")


class S3Client(S3ClientABC):
    """
    Wrapper for the AWS-provided S3 client. Mostly here to encapsulate the s3 client calls for
    other classes.
    """
    __slots__ = ['role', 's3'] # pragma: no mutate

    def __init__(self) -> None:
        super().__init__()
        self._init_s3_client()

    def _init_s3_client(self) -> None:
        """
        Populates self.s3 with a boto3 client which has assumed the role provided in the constructor.
        """
        print("S3 SETTINGS:", repr(settings.AWS_ROLE_ARN), repr(settings.AWS_ROLE_SESSION_NAME))
        sts = boto3.client('sts')

        assumed_role = sts.assume_role(
            RoleArn=settings.AWS_ROLE_ARN,
            RoleSessionName=settings.AWS_ROLE_SESSION_NAME
        )

        self.s3 = boto3.client(
            's3',
            aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
            aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
            aws_session_token=assumed_role['Credentials']['SessionToken']
        )

    def list_all_objects(self, bucket:str, prefix:str=None) -> Iterable[Dict[str,Any]]:
        """
        Provides an iterable of all objects in the bucket. If prefix is provided, it filters all data which doesn't
        start with prefix.
        """

        # the string constants in here are marked "pragma: no mutate" because changing them breaks the tests.
        # assemble a list of things in the billing bucket
        response = self.s3.list_objects_v2(Bucket=bucket) #, Prefix=prefix)

        # mutating this can break the test...
        items = list(response.get("Contents",[])) # pragma: no mutate
        yield from items

        while response.get('IsTruncated', False): # pragma: no mutate
            response = self.s3.list_objects_v2(Bucket=bucket, StartAfter=items[-1]['Key']) # pragma: no mutate
            items = list(response.get("Contents",[])) # pragma: no mutate
            yield from items

    def download(self, bucket:str, key:str) -> io.BytesIO:
        """
        Downloads a file with the given key from a bucket with the given name.

        Returns a file-like object.
        """
        string_file = io.BytesIO()
        self.s3.download_fileobj(bucket, key, string_file)
        return string_file

    def download_json(self, bucket:str, key:str) -> Any:
        """
        Downloads a file with the given key from a bucket with the given name, and parses
        it as json.
        """
        data = self.download(bucket, key)
        text_data = io.TextIOWrapper(data, newline=None)
        text_data.seek(0)
        return json.load(text_data)


class EventEmitter:
    """
    """
    events: Dict[str,Callable[...,None]]
    __slots__  = ['events'] # pragma: no mutate

    def __init__(self) -> None:
        super().__init__()
        self.events = collections.defaultdict(list)

    def on(self, name:str, cb:Callable[...,None]) -> None:
        self.events[name].append(cb)

    def off(self, name, cb:Callable[...,None]) -> None:
        self.events[name].remove(cb)

    def emit(self, name, *args, **kwds) -> None:
        for cb in self.events[name]:
            try:
                cb(*args, **kwds)
            except:
                # todo; we should throw a warning
                traceback.print_exc()
                pass


CreateClientFunc = Callable[[],S3ClientABC] # pragma: no mutate


class ReportScanner(EventEmitter):
    """
    This scans a provided list of buckets for the reports in them.

    This emits events pertaining to those reports, if they're updated or new report instances and versions
    are available. 
    """
    create_client_func: CreateClientFunc
    # scan_bucket needs to be in here for testing.
    __slots__ = ['create_client_func', '__dict__', 's3'] # pragma: no mutate

    def __init__(self, create_client_func:CreateClientFunc) -> None:
        super().__init__()
        self.create_client_func = create_client_func
        self.s3 = None

    def create_client(self) -> None:
        if self.s3 is None:
            self.s3 = self.create_client_func()
        return self.s3

    async def scan_buckets(self, buckets:List[Bucket], scanned_reports:AbstractSet[ReportVersion]=set()) -> None:
        for bucket in buckets:
            await self.scan_bucket(bucket, scanned_reports)

    async def scan_bucket(self, bucket:Bucket, scanned_reports:AbstractSet[ReportVersion]=set()) -> None:
        s3 = self.create_client()

        # TODO: test for exception during list_all_objects
        for item in s3.list_all_objects(bucket.name):
            match = CUR_MANIFEST_PATTERN.match(item['Key']) # pragma: no mutate
            if match is not None:
                matches = match.groupdict()
                for report in bucket.reports:
                    if report.prefix == matches['reportprefix'] and report.name == matches['reportname']:
                        manifest = s3.download_json(bucket.name, item['Key'])

                        etag = item['ETag'].strip('"')
                        keys = manifest['reportKeys']
                        assemblyid = manifest['assemblyId']
                        period = matches['period']
                        updated = item['LastModified']

                        report_version = ReportVersion(item['Key'], bucket.name, period, keys, assemblyid, updated, etag)

                        # TODO: test for failure here
                        if report_version not in scanned_reports:
                            #if await scanned_reports.add(bucket, report, report_version):
                            self.emit('report_changed', bucket, report, report_version)


class ReportPublisherABC:
    __slots__ = [] # pragma: no mutate
    async def publish_report_version(self, report_version) -> None:
        raise NotImplementedError("ReportPublisherABC is an abstract base class")


class ReportPublisher(ReportPublisherABC):
    __slots__ = ['report_repo', 'channel'] # pragma: no mutate

    def __init__(self, report_repo, channel) -> None:
        self.report_repo = report_repo
        self.channel = channel

    async def publish_report_version(self, report_version):
        """
        # TODO: if this fails between the insert into scanned invoices
        #       and the rabbitmq call, it can result in invoices not being
        #       processed.
        #
        #       use a transaction to insert the record into a tailable mongodb
        #       collection, as well as the scanned invoices list.
        #
        #       create a listener for the tailable mongodb collection and have it
        #       publish new items in the queue.
        """
        publish = await self.report_repo.upsert(report_version)

        # check if the cur has changed or is new
        if not publish:
            return

        # print some stuff for the log
        print('new or updated file:', report_version) # pragma: no mutate

        # publish if we should...
        # message, errors = schema.ReportVersion.dumps(report_version)

        for report_file in report_version.get_report_files():
            message, errors = schema.ReportFile.dumps(report_file)
            await self.channel.default_exchange.publish(
                aio_pika.Message(body=message.encode('utf-8')),
                routing_key = settings.INVOICE_UPDATE_QUEUE
            )


async def scan_invoices(loop, mongodb, rabbitmq):
    # get the collections together
    db = mongodb[settings.MONGODB_DB_NAME]
    bucket_collection = db[settings.BUCKET_LIST_COLLECTION_NAME]
    scanned_reports_collection = db[settings.SCANNED_INVOICE_COLLECTION_NAME]

    scanned_report_repo = ScannedReportRepo(scanned_reports_collection)
    scanner = ReportScanner(S3Client) # pragma: no mutate 

    bucket_repo = BucketRepo(bucket_collection)

    async with rabbitmq:
        # Creating channel
        report_update_channel = await rabbitmq.channel()
        await report_update_channel.set_qos(prefetch_count=1)

        scanned_reports = []
        async for scanned_report in scanned_report_repo.find():
            scanned_reports.append(scanned_report)

        new_reports = []
        scanner.on('report_changed', lambda bucket, report, report_version: new_reports.append(report_version)) # pragma: no mutate
        scanner.on('report_changed', lambda bucket, report, report_version: print('report_changed:', bucket, report, report_version)) # pragma: no mutate
        print('scanning')# pragma: no mutate
        buckets = []
        async for bucket in bucket_repo.find():
            buckets.append(bucket)
        await scanner.scan_buckets(buckets, scanned_reports)
        print('scan complete:',new_reports) # pragma: no mutate

        publisher = ReportPublisher(scanned_report_repo, report_update_channel)

        for report in new_reports:
            # find the most recent report
            await publisher.publish_report_version(report)


async def main(loop):
    # set up external connections
    mongodb = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_HOST, settings.MONGODB_PORT)

    rabbitmq = await aio_pika.connect_robust(
        settings.RABBITMQ_URL, loop=loop
    )

    await scan_invoices(loop, mongodb, rabbitmq)


if __name__ == "__main__": # pragma: no mutate
    # not woth testing
    loop = asyncio.get_event_loop() # pragma: no mutate
    loop.run_until_complete(main(loop)) # pragma: no mutate
    loop.close() # pragma: no mutate

