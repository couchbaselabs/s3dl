from __future__ import division, print_function

from concurrent import futures
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
        self._lock = threading.Lock()
        self._last = 0

    def add_file(self, bucket, key):
        with self._lock:
            uri = "s3://{}/{}".format(bucket, key)

            self._size[uri] += s3_client.head_object(
                Bucket=bucket, Key=key)['ContentLength']

        return functools.partial(self.update, uri)

    def update(self, uri, bytes_amount):
        with self._lock:
            self._seen_so_far[uri] += bytes_amount
            self.draw()

    def draw(self):
        if self._last:
            sys.stdout.write("\033[{}A".format(self._last))
        self._last = 0
        for key in sorted(self._size):
            percentage = (self._seen_so_far[key] / self._size[key]) * 100
            sys.stdout.write(
                "%s %s / %s  (%.2f%%)\n" % (key, self._seen_so_far[key], self._size[key], percentage))
            self._last += 1
        percentage = (sum(self._seen_so_far.values())/sum(self._size.values())) * 100
        sys.stdout.write(
            "Total %s / %s  (%.2f%%)\n" % (sum(self._seen_so_far.values()), sum(self._size.values()), percentage))
        self._last += 1
        sys.stdout.flush()


progress = ProgressPercentage()


def download(bucket, key, file, executor):
    downloader = transfer.MultipartDownloader(s3_client,
                                              transfer.TransferConfig(),
                                              transfer.OSUtils(),
                                              executor)

    downloader.download_file(bucket, key, file, s3_client.head_object(
            Bucket=bucket, Key=key)['ContentLength'], {},
                                callback=progress.add_file(bucket, key))

def main():
    if len(sys.argv) == 1 or '-h' in sys.argv or '--help' in sys.argv:
        print("Usage: s3dl s3://<bucket>/<key> [s3://<bucket>/<key>] ..",
              file=sys.stderr)

    urls = sys.argv[1:]
    def executor(*args, **kwargs):
        return futures.ThreadPoolExecutor(10)
    signal.signal(signal.SIGINT, signal_handler)

    with futures.ThreadPoolExecutor(len(urls)) as lexecutor:
        fut = []
        for url in urls:
            if not url.startswith('s3://'):
                raise ValueError("{} is not a valid s3 URI".format(url))

            bucket, key = url[5:].split('/', 1)
            file = key.split('/')[-1]
            fut.append(lexecutor.submit(
                    functools.partial(download, bucket, key, file, executor)))
        while(not all([f.done() for f in fut])):
            time.sleep(1)
        [f.result() for f in fut]


if __name__ == '__main__':
    sys.exit(main())