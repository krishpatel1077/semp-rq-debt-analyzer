"""
S3 client for managing knowledge base documents
"""
import boto3
from typing import List, Dict, Optional, Iterator
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger
from config.settings import get_aws_config, settings


class S3KnowledgeBaseClient:
    """Client for managing SEMP knowledge base in S3"""
    
    def __init__(self):
        try:
            self.s3_client = boto3.client('s3', **get_aws_config())
            self.bucket = settings.s3_knowledge_base_bucket
            self.prefix = settings.s3_knowledge_base_prefix
            logger.info(f"S3 client initialized for bucket: {self.bucket}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure your credentials.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def list_documents(self) -> List[Dict[str, str]]:
        """List all documents in the knowledge base"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=self.prefix
            )
            
            documents = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Skip folders
                    if not obj['Key'].endswith('/'):
                        documents.append({
                            'key': obj['Key'],
                            'filename': obj['Key'].split('/')[-1],
                            'size': obj['Size'],
                            'modified': obj['LastModified'].isoformat(),
                        })
            
            logger.info(f"Found {len(documents)} documents in knowledge base")
            return documents
            
        except ClientError as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    def download_document(self, key: str) -> Optional[bytes]:
        """Download a specific document by key"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            content = response['Body'].read()
            logger.info(f"Downloaded document: {key} ({len(content)} bytes)")
            return content
            
        except ClientError as e:
            logger.error(f"Failed to download document {key}: {e}")
            return None
    
    def download_document_stream(self, key: str) -> Optional[Iterator[bytes]]:
        """Download a document as a stream for large files"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            logger.info(f"Started streaming download for: {key}")
            return response['Body'].iter_chunks(chunk_size=8192)
            
        except ClientError as e:
            logger.error(f"Failed to stream document {key}: {e}")
            return None
    
    def get_document_metadata(self, key: str) -> Optional[Dict]:
        """Get metadata for a specific document"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=key)
            metadata = {
                'size': response['ContentLength'],
                'content_type': response.get('ContentType', 'unknown'),
                'modified': response['LastModified'].isoformat(),
                'metadata': response.get('Metadata', {}),
            }
            return metadata
            
        except ClientError as e:
            logger.error(f"Failed to get metadata for {key}: {e}")
            return None
    
    def document_exists(self, key: str) -> bool:
        """Check if a document exists in the knowledge base"""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False
    
    def upload_document(self, key: str, content: bytes, metadata: Optional[Dict] = None) -> bool:
        """Upload a document to the knowledge base"""
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
                
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                **extra_args
            )
            logger.info(f"Uploaded document: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to upload document {key}: {e}")
            return False