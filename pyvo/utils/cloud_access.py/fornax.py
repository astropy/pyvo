
import os
import requests
import json
import warnings
import logging
import threading

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s | %(name)s | %(message)s")
log = logging.getLogger('fornax')


from astropy.utils.data import download_file
from astropy.utils.console import ProgressBarOrSpinner

import boto3
import botocore

from botocore.client import Config



class DataHandler:
    """A base class that handles the different ways data can be accessed.
    The base implementation is to use on-prem data. Subclasses can handle 
    cloud data from aws, azure, google cloud etc.
    
    Subclasses can also handle authentication if needed.
    
    """
    
    
    def __init__(self, product):
        """Create a DataProvider object.
        
        Parameters:
            product: ~astropy.table.Row. The data url is accessed
                    in product['access_url']
        
        """
        self.product = product
        self.access_url = product['access_url']
        
    
    
    def download_file_http(self):
        """Download data in self.url using http"""
        log.info('--- Downloading data from on-prem ---')
        return download_file(self.access_url)
    
    
    def download(self):
        """Download data. Can be overloaded with different implimentation"""
        return self.download_file_http()

    
    
class AWSDataHandler(DataHandler):
    """Class for managaing access to data in AWS"""
    
    def __init__(self, product, profile=None, **kwargs):
        """Handle AWS-specific authentication and data download
        
        Parameters:
            product: ~astropy.table.Row. aws-s3 information should be available in
                     product['cloud_access'], otherwise, fall back to on-prem using
                     product['access_url']
            profile: name of the user's profile for credentials in ~/.aws/config 
                     or ~/.aws/credentials. If provided, we AWS api to authenticate 
                     the user using boto3. If None, use anonymous user. 
        
        """
        
        super().__init__(product)
        
        # if user_pays selected, a valid profile is required #
        user_pays = kwargs.get('user_pays', False)
        if user_pays and profile is None:
            raise botocore.exceptions.UnknownCredentialError('user_pays selected but no user info provided')
        
        
        # is the data in the cloud?
        data_in_aws  = False
        cloud_info = None
        if 'cloud_access' in product.keys():
            # read json provided by the archive
            cloud_access_json = product['cloud_access']
            cloud_access = json.loads(cloud_access_json)

            # is the data in aws?
            if 'aws' in cloud_access:
                data_in_aws = True
                cloud_info  = cloud_access['aws']
                
                if cloud_info['path'][0] == '/':
                    cloud_info['path'] = cloud_info['path'][1:]
            
            
        
        
        self.data_in_aws = data_in_aws
        self.cloud_info  = cloud_info
        self.user_pays   = user_pays
        self.profile     = profile
        

        
        
    def download(self, **kwargs):
        """Download data, from aws if possible, else from on-prem"""
        
            
        # if user or data are not in aws; fall to on-prem
        if not self.data_in_aws:
            log.info('Data not in the cloud, falling to on-prem ...')
            return self.download_file_http()
            
        
        user_on_aws = self.user_on_aws()
        if not user_on_aws:
            log.info('User not in the cloud, falling to on-prem ...')
            return self.download_file_http()
        
        
        # TODO: more error trapping in case some info is missing
        # read data info provided in cloud_access
        data_region = self.cloud_info['region']
        data_access = self.cloud_info['access'] # open | region | none
        
        log.info(f'data region: {data_region}')
        log.info(f'data access mode: {data_access}')
        
        
        
        # data on aws not accessible for some reason
        if data_access == 'none':
            log.info('Data access mode is "none", falling to on-prem ...')
            return self.download_file_http()
        
        # only in-region access is allowed
        if data_access == 'region':
            user_region = self.user_region()
            log.info(f'user region: {user_region}')
            if data_region == user_region:
                log.info('data_access=region; Data and user are in the same region; ')
            elif self.user_pays:
                log.info('data_access=region; Data and user are not in the same region, and user_pays is ENABLED')
            else:
                log.info('data_access=region; Data and user are not in the same region, and user_pays not enabled')
                return self.download_file_http()
        
        if data_access == 'open':
            log.info('Data mode is "open". Data is fully public.')
                
        
        
        # if we are here, we either have:
        # data_access=open, or data_access=region with either user_pays=True or user/data in same region
        # we handle each case separatly:
        
        # data is fully-open or open in region; use anonymous user
        if data_access == 'open' or (data_access == 'region' and data_region == user_region):
            session = None
            resource = boto3.resource(
                service_name = 's3', 
                config = botocore.client.Config(signature_version=botocore.UNSIGNED)
            )
        else:
            log.info('Data mode is "in-region". User credentials provided. Using them ...')
            # we have user credentials
            session = boto3.session.Session(profile_name=self.profile)
            resource = session.resource(service_name='s3')

        self.s3_client   = resource.meta.client
        self.session     = session
        self.s3_resource = resource
        self.download_file_s3(**kwargs)
    
    
    # borrowed from astroquery.mast.
    def download_file_s3(self, local_path=None, cache=True):
        """
        downloads the product used in inializing this object into
        the given directory.
        Parameters
        ----------
        local_path : str
            The local filename to which toe downloaded file will be saved.
        cache : bool
            Default is True. If file is found on disc it will not be downloaded again.
        """
        log.info('--- Downloading data from S3 ---')

        s3 = self.s3_resource
        s3_client = self.s3_client
        
        bucket_path = self.cloud_info['path']
        bucket_name = self.cloud_info['bucket']
        bkt = s3.Bucket(bucket_name)
        if not bucket_path:
            raise Exception(f"Unable to locate file {bucket_path}.")
            
        ## TODO: handle this in a better way
        if local_path is None:
            local_path = bucket_path.strip('/').split('/')[-1]

        # Ask the webserver (in this case S3) what the expected content length is and use that.
        info_lookup = s3_client.head_object(Bucket=bucket_name, Key=bucket_path)
        length = info_lookup["ContentLength"]

        if cache and os.path.exists(local_path):
            if length is not None:
                statinfo = os.stat(local_path)
                if statinfo.st_size != length:
                    log.infoing("Found cached file {0} with size {1} that is "
                                "different from expected size {2}"
                                .format(local_path,
                                        statinfo.st_size,
                                        length))
                else:
                    log.info("Found cached file {0} with expected size {1}."
                             .format(local_path, statinfo.st_size))
                    return

        with ProgressBarOrSpinner(length, ('Downloading URL s3://{0}/{1} to {2} ...'.format(
                bucket_name, bucket_path, local_path))) as pb:

            # Bytes read tracks how much data has been received so far
            # This variable will be updated in multiple threads below
            global bytes_read
            bytes_read = 0

            progress_lock = threading.Lock()

            def progress_callback(numbytes):
                # Boto3 calls this from multiple threads pulling the data from S3
                global bytes_read

                # This callback can be called in multiple threads
                # Access to updating the console needs to be locked
                with progress_lock:
                    bytes_read += numbytes
                    pb.update(bytes_read)

            bkt.download_file(bucket_path, local_path, Callback=progress_callback)
        
    
    
    
    def user_on_aws(self):
        """Check if the user is in on aws
        the following works for aws, but it is not robust enough
        This is partly from: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/identify_ec2_instances.html
        
        Comments in user_region below are also relevant here.
        
        """
        uuid = '/sys/hypervisor/uuid'
        is_aws =  os.path.exists(uuid) or 'AWS_REGION' in os.environ
        return is_aws
    
    
    def user_region(self):
        """Find region of the user in an ec2 instance.
        There could be a way to do it with the python api instead of an http request.
        
        This may be complicated:
        Instance metadata (including region) can be access from the link-local address
        169.254.169.254 (https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-identity-documents.html)
        So a simple http request to http://169.254.169.254/latest/dynamic/instance-identity/document gives
        a json response that has the region info in it.
        
        However, in jupyterhub, that address is blocked, because it may expose sensitive information about
        the instance and kubernetes cluster 
        (http://z2jh.jupyter.org/en/latest/administrator/security.html#audit-cloud-metadata-server-access).
        The region can be in $AWS_REGION
        """        
        
        region = os.environ.get('AWS_REGION', None)
        
        if region is None:
            # try the link-local address
            session = requests.session()
            response = session.get('http://169.254.169.254/latest/dynamic/instance-identity/document', timeout=2)
            region = response.json()['region']
            
        return region


    