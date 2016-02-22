from __future__ import division

from concurrent import futures
import functools
import os
import signal
import sys
import threading

import boto3
from boto3.s3 import transfer

s3_client = boto3.client('s3')

def signal_handler(signal, frame):
    print('Exiting!')
    os._exit(0)

class ProgressPercentage(object):
    def __init__(self):
        self._size = 0
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def add_file(self, bucket, key):
        with self._lock:
            self._size += s3_client.head_object(
                Bucket=bucket, Key=key)['ContentLength']
        return self

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s / %s  (%.2f%%)" % (self._seen_so_far, self._size, percentage))
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
    urls = sys.argv[1:]
    def executor(*args, **kwargs):
        return futures.ThreadPoolExecutor(10)
    signal.signal(signal.SIGINT, signal_handler)

    with futures.ThreadPoolExecutor(len(urls)) as lexecutor:
        fut = []
        for url in urls:
            if not url.startswith('s3://'):
                raise ValueError()

            bucket, key = url[5:].split('/', 1)
            file = key.split('/')[-1]
            f = functools.partial(download, bucket, key, file, executor)
            fut.append(lexecutor.submit(f))
        futures.wait(fut)

if __name__ == '__main__':
    sys.exit(main())