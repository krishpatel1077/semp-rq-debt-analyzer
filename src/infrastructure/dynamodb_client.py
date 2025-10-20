"""
DynamoDB client for chat history and agent information management
"""
import boto3
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from decimal import Decimal
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger
from config.settings import get_aws_config, settings


class DynamoDBChatClient:
    """Client for managing chat history and agent information in DynamoDB"""
    
    @staticmethod
    def convert_floats_to_decimal(obj: Any) -> Any:
        """Convert float values to Decimal and datetime to ISO string for DynamoDB compatibility"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: DynamoDBChatClient.convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [DynamoDBChatClient.convert_floats_to_decimal(item) for item in obj]
        else:
            return obj
    
    def __init__(self):
        try:
            self.dynamodb = boto3.resource('dynamodb', **get_aws_config())
            self.chat_table = self.dynamodb.Table(settings.dynamodb_chat_history_table)
            self.agent_table = self.dynamodb.Table(settings.dynamodb_agent_info_table)
            logger.info("DynamoDB client initialized successfully")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure your credentials.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB client: {e}")
            raise
    
    def create_chat_session(self, session_id: str, user_id: str = "default") -> bool:
        """Create a new chat session"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            self.chat_table.put_item(
                Item={
                    'session_id': session_id,
                    'user_id': user_id,
                    'created_at': timestamp,
                    'updated_at': timestamp,
                    'messages': [],
                    'session_status': 'active'
                }
            )
            logger.info(f"Created chat session: {session_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to create chat session {session_id}: {e}")
            return False
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """Add a message to a chat session"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Convert floats to Decimal for DynamoDB compatibility
            converted_metadata = self.convert_floats_to_decimal(metadata or {})
            
            message = {
                'role': role,  # 'user', 'assistant', 'system'
                'content': content,
                'timestamp': timestamp,
                'metadata': converted_metadata
            }
            
            # Add message to the session
            self.chat_table.update_item(
                Key={'session_id': session_id},
                UpdateExpression='SET messages = list_append(if_not_exists(messages, :empty_list), :message), updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':message': [message],
                    ':timestamp': timestamp,
                    ':empty_list': []
                }
            )
            
            logger.info(f"Added {role} message to session {session_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
            return False
    
    def get_chat_history(self, session_id: str, limit: Optional[int] = None) -> Optional[List[Dict]]:
        """Get chat history for a session"""
        try:
            response = self.chat_table.get_item(Key={'session_id': session_id})
            
            if 'Item' not in response:
                logger.warning(f"Chat session {session_id} not found")
                return None
            
            messages = response['Item'].get('messages', [])
            
            # Apply limit if specified
            if limit and len(messages) > limit:
                messages = messages[-limit:]
            
            logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
            return messages
            
        except ClientError as e:
            logger.error(f"Failed to get chat history for session {session_id}: {e}")
            return None
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information"""
        try:
            response = self.chat_table.get_item(Key={'session_id': session_id})
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            return {
                'session_id': item['session_id'],
                'user_id': item.get('user_id', 'default'),
                'created_at': item['created_at'],
                'updated_at': item['updated_at'],
                'session_status': item.get('session_status', 'active'),
                'message_count': len(item.get('messages', []))
            }
            
        except ClientError as e:
            logger.error(f"Failed to get session info for {session_id}: {e}")
            return None
    
    def list_user_sessions(self, user_id: str = "default", limit: int = 20) -> List[Dict]:
        """List recent sessions for a user"""
        try:
            # Note: This requires a GSI on user_id for efficient querying
            response = self.chat_table.scan(
                FilterExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id},
                Limit=limit
            )
            
            sessions = []
            for item in response.get('Items', []):
                sessions.append({
                    'session_id': item['session_id'],
                    'created_at': item['created_at'],
                    'updated_at': item['updated_at'],
                    'session_status': item.get('session_status', 'active'),
                    'message_count': len(item.get('messages', []))
                })
            
            # Sort by updated_at descending
            sessions.sort(key=lambda x: x['updated_at'], reverse=True)
            
            logger.info(f"Found {len(sessions)} sessions for user {user_id}")
            return sessions
            
        except ClientError as e:
            logger.error(f"Failed to list sessions for user {user_id}: {e}")
            return []
    
    def update_session_status(self, session_id: str, status: str) -> bool:
        """Update session status (active, completed, archived)"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            self.chat_table.update_item(
                Key={'session_id': session_id},
                UpdateExpression='SET session_status = :status, updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':status': status,
                    ':timestamp': timestamp
                }
            )
            
            logger.info(f"Updated session {session_id} status to {status}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to update session status for {session_id}: {e}")
            return False
    
    def store_agent_info(self, agent_id: str, agent_data: Dict) -> bool:
        """Store agent configuration or state information"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Convert floats to Decimal for DynamoDB compatibility
            converted_data = self.convert_floats_to_decimal(agent_data)
            
            item = {
                'agent_id': agent_id,
                'updated_at': timestamp,
                **converted_data
            }
            
            self.agent_table.put_item(Item=item)
            logger.info(f"Stored agent info for: {agent_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to store agent info for {agent_id}: {e}")
            return False
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict]:
        """Get agent configuration or state information"""
        try:
            response = self.agent_table.get_item(Key={'agent_id': agent_id})
            
            if 'Item' not in response:
                return None
            
            return response['Item']
            
        except ClientError as e:
            logger.error(f"Failed to get agent info for {agent_id}: {e}")
            return None