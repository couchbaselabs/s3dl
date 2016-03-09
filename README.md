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

s3dl will use AWS profile identified by the S3_DEFAULT_PROFILE environment 
variable if set; otherwise it will use the AWS default profile.

## Usage

When installed with pip, s3dl will be appropriately registered and usable
directly from the command line.

    s3dl s3://<bucket-name>/<key-name> s3://<bucket-name2>/<key-name2>