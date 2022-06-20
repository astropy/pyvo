
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
        
    
    def process_data_info(self):
        """Process data product info """
        log.info('--- Using data from on-prem ---')
        info = {'access_url': self.access_url}
        return info
    
    
    def download(self):
        """Download data. Can be overloaded with different implimentation"""
        info = self.process_data_info()
        return download_file(info['access_url'])

    
    
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
        
            
        # set variables to be used elsewhere
        self.requester_pays = kwargs.get('requester_pays', False)
        self.profile = profile
        self.product = product
        
        
    
    def _validate_aws_info(self, info):
        """Do some basic validation of the json info in the cloud_access column
        
        info: a dictionary serialized from the json text returned in the cloud_access
            column returned with the data product
        
        """
        
        # TODO; more rigorous checks
        keys = list(info.keys())
        assert('region' in keys)
        assert('access' in keys)
        assert('bucket' in keys)
        assert('path' in keys)
        
        
        if info['path'][0] == '/':
            info['path'] = info['path'][1:]
        
        return info

    
    
    def process_data_info(self):
        """Process data product info """
        
        # info dict to be filled and returned
        info = {'access_url': self.access_url}
        
        
        # is the user on aws? if not, fall back to on-perm
        user_on_aws = self.user_on_aws()
        if not user_on_aws:
            log.info('User not in the cloud, falling to on-prem ...')
            return info
        
        
        # do we have cloud_access info in the data product?
        if not 'cloud_access' in self.product.keys():
            log.info('Input product does not have any cloud access information')
            return info
        
        
        # read json provided by the archive server
        cloud_access = json.loads(self.product['cloud_access'])
        
        # do we have information specific to aws in the data product?
        if not 'aws' in cloud_access:
            log.info('No aws cloud access information in the data product')
            return info
        
        
        # we have info about data in aws; validate it first #
        aws_info = cloud_access['aws']
        aws_info = self._validate_aws_info(aws_info)
        
        
        data_region = aws_info['region']
        data_access = aws_info['access'] # open | region | none
        log.info(f'data region: {data_region}')
        log.info(f'data access mode: {data_access}')
        
        
        # data on aws not accessible for some reason
        if data_access == 'none':
            log.info('Data access mode is "none", falling to on-prem ...')
            return info
        
        # save information needed to access the file
        info['s3_path']   = aws_info['path']
        info['s3_bucket'] = aws_info['bucket']
        
            
        # data have open access 
        if data_access == 'open':
            log.info('Accessing public data on aws ...')
            s3_config = botocore.client.Config(signature_version=botocore.UNSIGNED)
            s3_resource = boto3.resource(service_name='s3', config=s3_config)
            info['s3_resource'] = s3_resource
            return info
                
        
        if data_access == 'region':
            log.info(f'data_access=region; data_region: {data_region} ')
            
            # user region
            user_region = self.user_region()
            log.info(f'user region: {user_region}')
            
            # if same region as data, proceed
            if data_region == user_region:
                log.info('data and user in the same region')
                s3_resource = boto3.resource(service_name='s3', region_name=user_region)
                info['s3_resource'] = s3_resource
                return info
            
            
            # user_region != data_region, but requester_pays
            if self.requester_pays:
                log.info('Data mode is "region", with requester_pays')
                if self.profile is None:
                    raise Exception('requester_pays selected but no user info provided')
                
                # we have user credentials
                session = boto3.session.Session(profile_name=self.profile)
                resource = session.resource(service_name='s3')
                info['s3_resource'] = s3_resource
                return info
                
            log.info('data_region != user_region. Fall back to on-prem')
        
        
        # if no conidtion is satisfied, at least access_url should befine
        assert('access_url' in info.keys())
            
        return info
        
        
        
    def download(self, **kwargs):
        """Download data, from aws if possible, else from on-prem"""
        
        data_info = self.process_data_info()
        
        # if no s3_resource object, default to http download
        if 's3_resource' in data_info.keys():
            log.info('--- Downloading data from S3 ---')
            self._download_file_s3(data_info, **kwargs)
        else:
            log.info('--- Downloading data from On-prem ---')
            download_file(data_info['access_url'])
    
    
    # adapted from astroquery.mast.
    def _download_file_s3(self, data_info, local_path=None, cache=True):
        """
        downloads the product used in inializing this object into
        the given directory.
        Parameters
        ----------
        data_info : dict holding the data information, with keys for:
            s3_resource, s3_path, s3_bucket
        local_path : str
            The local filename to which toe downloaded file will be saved.
        cache : bool
            Default is True. If file is found on disc it will not be downloaded again.
        """

        s3 = data_info['s3_resource']
        s3_client = s3.meta.client
        
        bucket_path = data_info['s3_path']
        bucket_name = data_info['s3_bucket']
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


    