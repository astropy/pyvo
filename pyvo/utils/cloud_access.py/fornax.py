
import os
import requests

import boto3
import botocore

from botocore.client import Config


class Context:
    """Context Class to do the configuration and context exploration"""
    
    cloud_datasets = ['hst', 'spitzer', 'xmm']
    
    
    def __init__(self, uri, profile=None, **kwargs):
        """Initialize a Context object
        
        uri: the uri of the data
        profile: name of the user profile for credentials in ~/.aws/config 
            or ~/.aws/credentials. If None, use anonymous user.
        
        
        """
        
        self.provider = kwargs.get('provider', 'aws')
        
        
        # clean uri #
        mission, bucket, path = process_data_uri(uri)
        
        
        http = False
        requester_pays = False
        
        # user and data in the cloud?
        if user_in_cloud() and data_in_cloud():
            # Both user and data in the cloud.
            
                
            # user and data in the same region?
            # if user_in_fornax, we are in the same region by design
            region_match = user_in_fornax() or user_region() == bucket_region(bucket)

            if not region_match:
                if cross_region_transfer():
                    requester_pays = True
                else:
                    # falls back to http
                    http = True
        else:
            # either user or data not in the cloud
            http = True
        
        
        # handle the cases of s3 vs http:
        if http:
            # initialize a requests session
            self.session = requests.session()
        else:
            if profile is None:
                # anonymous 
                session = None
                resource = boto3.resource(
                    service_name = 's3', 
                    config = botocore.client.Config(signature_version=botocore.UNSIGNED)
                )
            else:
                # we have user credentials
                session = boto3.session.Session(profile_name=profile)
                resource = session.resource(service_name='s3')
            
            client = resource.meta.client

            self.session = session
            self.s3_resource = resource
            self.s3_client = client
        
        self.http = http
        self.requester_pays = requester_pays
        
    
    def process_data_uri(self, uri):
        """Process data uri to extract mission, bucket and path names"""
        uri_s = uri.split('/')
        mission = uri_s[0]
        bucket  = uri_s[1]
        path = '/'.join(uri_s[2:])
        return mission, bucket, path

        
    def user_in_cloud(self):
        """Check if the user is in the cloud
        the following works for aws. 
        This function may be used to figure out what cloud service we are in, if any?
        """
        return os.path.exists('/var/lib/cloud')
    
    
    def data_in_cloud(self, dataset):
        """Check if the requested data is available in the cloud"""
        # from some pre-defined cloud_datasets (either hard-coded or from an api)
        return dataset in self.cloud_datasets
    
    
    def user_in_fornax(self):
        """Check if user is using the nasa-platform"""
        return 'FORNAX' in os.environ
    
    
    def user_region(self):
        """Find region of the user.
        There could be a way to do it with the python api instead of an http request.
        
        """
        region = None
        if self.provider == 'aws':
            session = requests.session()
            response = session.get('http://169.254.169.254/latest/dynamic/instance-identity/document')
            region = response.json()['region']
        return region
    
    def cross_region_transfer(self):
        """Check if cross region data transfer is allowd by user settings"""
        #allow = some_user_config.allow_cross_region_transfer
        allow = False
        return allow
    
        

    def bucket_region(self, bucket):
        """Return the region of the bucket

        bucket: bucket name

        Note that according to [this](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketLocation.html), 
        you need to be the bucket owner to be able to use `s3_client.get_bucket_location(bucket)`, so it may not
        be general.
        
        The http api works by doing: curl --head $BUCKET_NAME.s3.amazonaws.com, and parsing for x-amz-bucket-region
        where BUCKET_NAME is a public dataset

        """
        region = None
        if self.provider == 'aws':
            session = requests.session()
            response = session.get(f'http://{bucket}.s3.amazonaws')
            region = response.json()['x-amz-bucket-region'] 
        return region
    
    

if __name__ == '__main__':
    
    # local computer