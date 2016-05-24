# s3dl
s3dl is a command-line program for downloading files from S3 in parallel.

## Install
You can install s3dl straight from the repository by using pip:

    pip install git+https://github.com/couchbaselabs/s3dl.git

Alternatively for development purposes you can install s3dl locally:

    git clone https://github.com/couchbaselabs/s3dl.git
    pip install -e s3dl

### Configuration
s3dl requires default boto configuration 
(http://boto3.readthedocs.org/en/latest/guide/configuration.html). The easiest
way to do this is through awscli:

    pip install awscli
    aws configure [--profile profile-name]

s3dl will use AWS profile identified by the S3DL_DEFAULT_PROFILE environment 
variable if set; otherwise it will use the AWS default profile.

## Usage

When installed with pip, s3dl will be appropriately registered and usable
directly from the command line.

    s3dl s3://<bucket-name>/<key-name> s3://<bucket-name2>/<key-name2>

The --no-clobber (-nc) flag can be used to prevent overwriting files which have
previously been downloaded:

    $ s3dl s3://my-bucket/my-key.txt
    s3://my-bucket/my-key.txt 5KiB / 5KiB  (100.00%)
    Total 5KiB / 5KiB  (100.00%)

    $ ls
    my-key.txt

    $ s3dl s3://my-bucket/my-key.txt --no-clobber
    Skipping s3://my-bucket/my-key.txt (no clobber)

If no URLs are specified on the command line then s3dl will check if it is
being piped into from stdin and will read a list of file to download from
stdin:

    $ cat urls.txt
    s3://my-bucket/my-key.txt
    s3://my-bucket/my-key2.txt

    $ cat urls.txt | s3dl
    s3://my-bucket/my-key.txt 0.6KiB / 136.5KiB  (0.44%)
    s3://my-bucket/my-key2.txt 1.7KiB / 143.5KiB  (1.15%)
    Total 2.2KiB / 280.0KiB  (0.80%)
