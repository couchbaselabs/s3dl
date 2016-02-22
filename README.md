# s3dl
s3dl is a command-line program for downloading files from S3 in parallel.

## Install
You can install s3dl straight from the repository by using pip:

    pip install git+https://github.com/couchbaselabs/s3dl.git

Alternatively for development purposes you can install s3dl locally:

    git clone https://github.com/couchbaselabs/s3dl.git
    pip install -e s3dl

### Configuration
s3dl requires default boto configuration. The easiest way to do this is through
awscli:

    pip install awscli
    aws configure

## Usage

When installed with pip, s3dl will be appropriately registered and usable
directly from the command line.

    s3dl s3://<bucket-name>/<key-name> s3://<bucket-name2>/<key-name2>