"""
AWS Bedrock client for LLM and embeddings
"""
import json
import boto3
import numpy as np
from typing import List, Dict, Any
from loguru import logger
from botocore.exceptions import ClientError, NoCredentialsError

from config.settings import get_aws_config, get_bedrock_config


class BedrockClient:
    """Client for AWS Bedrock LLM and embeddings"""
    
    def __init__(self):
        try:
            aws_config = get_aws_config()
            bedrock_config = get_bedrock_config()
            
            # Initialize Bedrock Runtime client
            self.bedrock_runtime = boto3.client(
                'bedrock-runtime',
                region_name=bedrock_config["region"],
                **aws_config
            )
            
            self.model_id = bedrock_config["model_id"]
            self.embedding_model_id = bedrock_config["embedding_model_id"]
            
            logger.info(f"Bedrock client initialized with model: {self.model_id}")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure your credentials.")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise
    
    def generate_text(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Generate text using Bedrock LLM"""
        try:
            # Default parameters for Claude
            default_params = {
                "max_tokens": kwargs.get("max_tokens", 4000),
                "temperature": kwargs.get("temperature", 0.3),
                "top_p": kwargs.get("top_p", 0.9),
                "stop_sequences": kwargs.get("stop_sequences", [])
            }
            
            # Build request body based on model type
            if "anthropic.claude" in self.model_id.lower():
                request_body = self._build_claude_request(prompt, system_prompt, default_params)
            elif "amazon.titan" in self.model_id.lower():
                request_body = self._build_titan_request(prompt, default_params)
            else:
                # Generic request format
                request_body = {
                    "inputText": prompt,
                    "textGenerationConfig": default_params
                }
            
            # Make request to Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract text based on model type
            if "anthropic.claude" in self.model_id.lower():
                return response_body['content'][0]['text']
            elif "amazon.titan" in self.model_id.lower():
                return response_body['results'][0]['outputText']
            else:
                # Try common response formats
                if 'outputText' in response_body:
                    return response_body['outputText']
                elif 'content' in response_body:
                    return response_body['content']
                elif 'text' in response_body:
                    return response_body['text']
                else:
                    logger.warning(f"Unknown response format: {response_body}")
                    return str(response_body)
                    
        except ClientError as e:
            logger.error(f"Bedrock text generation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Text generation error: {e}")
            raise
    
    def get_embeddings(self, text: str) -> np.ndarray:
        """Get embeddings using Bedrock embeddings model"""
        try:
            # Build request based on embedding model
            if "amazon.titan-embed" in self.embedding_model_id.lower():
                request_body = {
                    "inputText": text
                }
            elif "cohere.embed" in self.embedding_model_id.lower():
                request_body = {
                    "texts": [text],
                    "input_type": "search_document"
                }
            else:
                # Generic format
                request_body = {
                    "inputText": text
                }
            
            # Make request to Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.embedding_model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract embeddings based on model type
            if "amazon.titan-embed" in self.embedding_model_id.lower():
                embedding = response_body['embedding']
            elif "cohere.embed" in self.embedding_model_id.lower():
                embedding = response_body['embeddings'][0]
            else:
                # Try common response formats
                if 'embedding' in response_body:
                    embedding = response_body['embedding']
                elif 'embeddings' in response_body:
                    embedding = response_body['embeddings'][0]
                else:
                    logger.error(f"Unknown embedding response format: {response_body}")
                    raise ValueError("Could not extract embedding from response")
            
            return np.array(embedding)
            
        except ClientError as e:
            logger.error(f"Bedrock embeddings failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Embeddings error: {e}")
            raise
    
    def _build_claude_request(self, prompt: str, system_prompt: str, params: Dict) -> Dict:
        """Build request body for Claude models"""
        messages = [{"role": "user", "content": prompt}]
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": params["max_tokens"],
            "temperature": params["temperature"],
            "top_p": params["top_p"],
            "messages": messages
        }
        
        if system_prompt:
            request_body["system"] = system_prompt
            
        if params["stop_sequences"]:
            request_body["stop_sequences"] = params["stop_sequences"]
        
        return request_body
    
    def _build_titan_request(self, prompt: str, params: Dict) -> Dict:
        """Build request body for Titan models"""
        return {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": params["max_tokens"],
                "temperature": params["temperature"],
                "topP": params["top_p"],
                "stopSequences": params["stop_sequences"]
            }
        }
    
    def test_connection(self) -> bool:
        """Test connection to Bedrock"""
        try:
            # Try a simple text generation
            response = self.generate_text("Hello", max_tokens=10)
            logger.info("Bedrock connection test successful")
            return True
        except Exception as e:
            logger.error(f"Bedrock connection test failed: {e}")
            return False