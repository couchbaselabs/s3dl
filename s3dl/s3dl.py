from __future__ import division, print_function

from concurrent import futures
import argparse
import collections
import functools
import os
import signal
import sys
import time
import threading

import boto3
from boto3.s3 import transfer

if os.environ.get('S3DL_DEFAULT_PROFILE', ''):
    boto3.setup_default_session(profile_name=os.environ.get(
            'S3DL_DEFAULT_PROFILE'))

s3_client = boto3.client('s3')


def signal_handler(signal, frame):
    print('\nExiting!')
    os._exit(0)


class ProgressPercentage(object):
    def __init__(self):
        self._size = collections.defaultdict(int)
        self._seen_so_far = collections.defaultdict(int)
        self._status = collections.defaultdict(str)
        self._lock = threading.Lock()
        self._last = 0

    def add_file(self, bucket, key):
        with self._lock:
            uri = "s3://{}/{}".format(bucket, key)
            self._status[uri] = 'Waiting'
            self._size[uri] += s3_client.head_object(
                Bucket=bucket, Key=key)['ContentLength']
            self.draw()

    def completed(self, bucket, key):
        with self._lock:
            uri = "s3://{}/{}".format(bucket, key)
            self._status[uri] = 'Completed'
            self.draw()

    def progress_callback(self, bucket, key):
        with self._lock:
            uri = "s3://{}/{}".format(bucket, key)
            self._status[uri] = 'Downloading'
            return functools.partial(self.update, uri)

    def update(self, uri, bytes_amount):
        with self._lock:
            self._seen_so_far[uri] += bytes_amount
            self.draw()

    @staticmethod
    def percentage(a, b):
        return (a / b) * 100

    @staticmethod
    def sizeof_fmt(a, b, suffix='B'):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(b) < 1024.0:
                return ("{:3.1f}{}{}".format(a, unit, suffix),
                        "{:3.1f}{}{}".format(b, unit, suffix))
            b /= 1024.0
            a /= 1024.0
        return ("{:.1f}{}{}".format(a, 'Yi', suffix),
                "{:.1f}{}{}".format(b, 'Yi', suffix))

    @classmethod
    def write_row(cls, key, seen, size, status=''):
        percent = cls.percentage(seen, size)
        seen_str, size_str = cls.sizeof_fmt(seen, size)
        sys.stdout.write("\033[K")
        sys.stdout.write("{} {} / {}  ({:.2f}%) {}\n".format(key,
                                                             seen_str,
                                                             size_str,
                                                             percent,
                                                             status))

    def draw(self):
        if self._last:
            sys.stdout.write("\033[{}A".format(self._last))
        self._last = len(self._size) + 1
        for key in sorted(self._size):
            self.write_row(key,
                           self._seen_so_far[key],
                           self._size[key],
                           status=self._status[key])

        self.write_row("Total",
                       sum(self._seen_so_far.values()),
                       sum(self._size.values()))

        sys.stdout.flush()


progress = ProgressPercentage()


def download_file(download):
    downloader = transfer.S3Transfer(s3_client,
                                     transfer.TransferConfig(),
                                     transfer.OSUtils())

    downloader.download_file(download.bucket,
                             download.key,
                             download.download_path,
                             callback=progress.progress_callback(
                                download.bucket,
                                download.key))
    progress.completed(download.bucket, download.key)
    if os.path.isfile(download.file_path):
        os.remove(download.file_path)
    os.rename(download.download_path, download.file_path)


def parse_arguments(args):
    class UniqueAppendAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            unique_values = set(values)
            setattr(namespace, self.dest, unique_values)

    parser = argparse.ArgumentParser()
    parser.add_argument('URI',
                        nargs='*',
                        action=UniqueAppendAction,
                        help='s3 URIs to download (e.g. s3://<bucket>/<file>)')
    parser.add_argument("-nc",
                        "--no-clobber",
                        help="don't overwrite existing files",
                        action="store_true",
                        default=False)
    parser.add_argument("-d",
                        "--directory",
                        type=str,
                        help="Directory to write files to",
                        action="store",
                        default=".")
    parser.add_argument("-p",
                        "--parallelism",
                        type=int,
                        help="Number of files to download at once",
                        action="store",
                        default=1)

    args = parser.parse_args(args[1:])

    if not args.URI and not sys.stdin.isatty():
        # [:-1] in order to remove \n character
        args.URI = [line[:-1] for line in sys.stdin]

    if not args.URI:
        parser.print_usage(sys.stderr)
        print("error: too few arguments")

    return args



class DownloadInfo(object):
    def __init__(self, bucket, key, file_path, no_clobber):
        self.bucket = bucket
        self.key = key
        self.file_path = file_path
        self.no_clobber = no_clobber

    @property
    def download_path(self):
        return self.file_path + ".nc"

    @classmethod
    def from_uri(cls, uri, download_directory, no_clobber):
        if not uri.startswith('s3://'):
            raise ValueError("'{}' is not a valid s3 URI".format(uri))
        bucket, key = uri[5:].split('/', 1)

        # Remove username prefix
        if '@' in bucket:
            bucket = bucket.split('@')[-1]

        # Filename
        filename = key.split('/')[-1]
        file_path = os.path.join(download_directory, filename)

        return cls(bucket, key, file_path, no_clobber)

    def clobbered(self):
        return os.path.isfile(self.file_path) and  self.no_clobber


def main(args=sys.argv):
    arguments = parse_arguments(args)
    signal.signal(signal.SIGINT, signal_handler)

    downloads = [
        DownloadInfo.from_uri(uri, arguments.directory, arguments.no_clobber)
        for uri in arguments.URI]
    skipped = [d for d in downloads if d.clobbered()]
    downloads = [d for d in downloads if not d.clobbered()]

    for skip in skipped:
        print("Skipping s3://{}/{} (no clobber)".format(skip.bucket, skip.key))

    with futures.ThreadPoolExecutor(arguments.parallelism) as lexecutor:


        # Submit downloads to executor
        fut = []
        for download in downloads:
            progress.add_file(download.bucket,
                              download.key)
            fut.append(lexecutor.submit(
                    functools.partial(download_file,
                                      download)))

        while(not all([f.done() for f in fut])):
            time.sleep(1)
        [f.result() for f in fut]
