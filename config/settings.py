"""
Configuration settings for SEMP Requirements Debt Analyzer
"""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # AWS Configuration
    aws_access_key_id: str = Field(..., env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(..., env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    
    # S3 Configuration
    s3_knowledge_base_bucket: str = Field(..., env="S3_KNOWLEDGE_BASE_BUCKET")
    s3_knowledge_base_prefix: str = Field(default="semp-docs/", env="S3_KNOWLEDGE_BASE_PREFIX")
    
    # DynamoDB Configuration
    dynamodb_chat_history_table: str = Field(..., env="DYNAMODB_CHAT_HISTORY_TABLE")
    dynamodb_agent_info_table: str = Field(..., env="DYNAMODB_AGENT_INFO_TABLE")
    
    # AWS Bedrock Configuration
    bedrock_model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0", env="BEDROCK_MODEL_ID")
    bedrock_embedding_model_id: str = Field(default="amazon.titan-embed-text-v1", env="BEDROCK_EMBEDDING_MODEL_ID")
    bedrock_region: str = Field(default="us-east-1", env="BEDROCK_REGION")
    
    # Application Configuration
    app_name: str = Field(default="SEMP Requirements Debt Analyzer", env="APP_NAME")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    max_chat_history: int = Field(default=50, env="MAX_CHAT_HISTORY")
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    environment: str = Field(default="dev", env="ENVIRONMENT")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


# Global settings instance
settings = Settings()


def get_aws_config() -> dict:
    """Get AWS configuration dictionary"""
    return {
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
        "region_name": settings.aws_region,
    }


def get_bedrock_config() -> dict:
    """Get AWS Bedrock configuration dictionary"""
    return {
        "model_id": settings.bedrock_model_id,
        "embedding_model_id": settings.bedrock_embedding_model_id,
        "region": settings.bedrock_region,
    }
