"""
RAG Knowledge Base processor using vecclean for embeddings and vector search
"""
import json
import pickle
from typing import List, Dict, Optional, Any
from pathlib import Path
import numpy as np
import openai
from vecclean import VectorStore
from loguru import logger

from config.settings import get_openai_config, settings
from src.infrastructure.s3_client import S3KnowledgeBaseClient
from src.rag.document_processor import DocumentProcessor


class SEMPKnowledgeBase:
    """Knowledge base for SEMP documents with RAG capabilities"""
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize clients
        self.s3_client = S3KnowledgeBaseClient()
        self.doc_processor = DocumentProcessor()
        
        # Initialize OpenAI
        openai_config = get_openai_config()
        openai.api_key = openai_config["api_key"]
        self.embedding_model = openai_config["embedding_model"]
        
        # Initialize vector store
        self.vector_store = VectorStore(
            dimension=1536,  # OpenAI ada-002 embedding dimension
            storage_path=str(self.cache_dir / "vector_store.pkl")
        )
        
        # Document metadata cache
        self.document_cache_path = self.cache_dir / "document_metadata.json"
        self.document_metadata = self._load_document_metadata()
        
        logger.info("SEMP Knowledge Base initialized")
    
    def initialize_knowledge_base(self, force_refresh: bool = False) -> bool:
        """Initialize or refresh the knowledge base from S3"""
        try:
            logger.info("Initializing knowledge base...")
            
            # Get list of documents from S3
            documents = self.s3_client.list_documents()
            
            if not documents:
                logger.warning("No documents found in S3 knowledge base")
                return False
            
            # Check if we need to process any documents
            documents_to_process = []
            
            for doc in documents:
                doc_key = doc['key']
                if force_refresh or not self._is_document_processed(doc_key, doc['modified']):
                    documents_to_process.append(doc)
            
            if not documents_to_process:
                logger.info("All documents are up to date")
                return True
            
            logger.info(f"Processing {len(documents_to_process)} documents")
            
            # Process documents
            for doc in documents_to_process:
                success = self._process_document(doc)
                if not success:
                    logger.error(f"Failed to process document: {doc['filename']}")
            
            # Save document metadata
            self._save_document_metadata()
            
            # Save vector store
            self.vector_store.save()
            
            logger.info("Knowledge base initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base: {e}")
            return False
    
    def search_knowledge_base(self, query: str, top_k: int = 5, score_threshold: float = 0.7) -> List[Dict]:
        """Search the knowledge base for relevant information"""
        try:
            # Get query embedding
            query_embedding = self._get_embedding(query)
            
            # Search vector store
            results = self.vector_store.search(
                query_embedding,
                top_k=top_k,
                score_threshold=score_threshold
            )
            
            # Format results with metadata
            formatted_results = []
            for result in results:
                chunk_data = result.get('metadata', {})
                formatted_results.append({
                    'text': result.get('text', ''),
                    'score': result.get('score', 0.0),
                    'document': chunk_data.get('document_name', 'unknown'),
                    'chunk_index': chunk_data.get('chunk_index', 0),
                    'document_type': chunk_data.get('document_type', 'unknown'),
                    'metadata': chunk_data
                })
            
            logger.info(f"Found {len(formatted_results)} relevant chunks for query")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search knowledge base: {e}")
            return []
    
    def get_document_context(self, document_names: List[str] = None) -> List[Dict]:
        """Get context from specific documents or all documents"""
        try:
            if document_names:
                # Filter chunks by document names
                all_chunks = self.vector_store.get_all_vectors()
                filtered_chunks = []
                
                for chunk in all_chunks:
                    chunk_metadata = chunk.get('metadata', {})
                    if chunk_metadata.get('document_name') in document_names:
                        filtered_chunks.append({
                            'text': chunk.get('text', ''),
                            'document': chunk_metadata.get('document_name', 'unknown'),
                            'chunk_index': chunk_metadata.get('chunk_index', 0),
                            'metadata': chunk_metadata
                        })
                
                return filtered_chunks
            else:
                # Return all chunks
                return self.get_all_chunks()
                
        except Exception as e:
            logger.error(f"Failed to get document context: {e}")
            return []
    
    def get_all_chunks(self) -> List[Dict]:
        """Get all text chunks in the knowledge base"""
        try:
            all_vectors = self.vector_store.get_all_vectors()
            chunks = []
            
            for vector_data in all_vectors:
                chunk_metadata = vector_data.get('metadata', {})
                chunks.append({
                    'text': vector_data.get('text', ''),
                    'document': chunk_metadata.get('document_name', 'unknown'),
                    'chunk_index': chunk_metadata.get('chunk_index', 0),
                    'metadata': chunk_metadata
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get all chunks: {e}")
            return []
    
    def _process_document(self, doc_info: Dict) -> bool:
        """Process a single document"""
        try:
            doc_key = doc_info['key']
            filename = doc_info['filename']
            
            logger.info(f"Processing document: {filename}")
            
            # Download document
            content = self.s3_client.download_document(doc_key)
            if not content:
                logger.error(f"Failed to download document: {filename}")
                return False
            
            # Get document metadata
            doc_metadata = self.s3_client.get_document_metadata(doc_key)
            content_type = doc_metadata.get('content_type', 'unknown') if doc_metadata else 'unknown'
            
            # Extract text
            text = self.doc_processor.extract_text(content, filename, content_type)
            if not text:
                logger.error(f"Failed to extract text from: {filename}")
                return False
            
            # Create chunks
            chunk_metadata = {
                'document_name': filename,
                'document_key': doc_key,
                'document_type': self._classify_document_type(filename),
                'content_type': content_type,
                'size': doc_info.get('size', 0),
                'modified': doc_info.get('modified', '')
            }
            
            chunks = self.doc_processor.chunk_text(text, chunk_metadata)
            
            # Generate embeddings and add to vector store
            for chunk in chunks:
                embedding = self._get_embedding(chunk['text'])
                
                # Add to vector store
                self.vector_store.add_vector(
                    vector=embedding,
                    text=chunk['text'],
                    metadata={
                        **chunk_metadata,
                        'chunk_index': chunk['chunk_index'],
                        'word_count': chunk['word_count'],
                        'char_count': chunk['char_count']
                    }
                )
            
            # Update document metadata
            self.document_metadata[doc_key] = {
                'filename': filename,
                'processed_at': doc_info.get('modified', ''),
                'chunk_count': len(chunks),
                'document_type': chunk_metadata['document_type']
            }
            
            logger.info(f"Successfully processed {filename} into {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process document {doc_info.get('filename', 'unknown')}: {e}")
            return False
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text using OpenAI"""
        try:
            response = openai.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            embedding = np.array(response.data[0].embedding)
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            raise
    
    def _classify_document_type(self, filename: str) -> str:
        """Classify document type based on filename"""
        filename_lower = filename.lower()
        
        if 'semp' in filename_lower:
            return 'SEMP'
        elif 'requirement' in filename_lower:
            return 'Requirements'
        elif 'guide' in filename_lower or 'guideline' in filename_lower:
            return 'Guide'
        elif 'standard' in filename_lower:
            return 'Standard'
        elif 'debt' in filename_lower:
            return 'Debt_Detection'
        else:
            return 'General'
    
    def _is_document_processed(self, doc_key: str, modified_date: str) -> bool:
        """Check if document has been processed and is up to date"""
        if doc_key not in self.document_metadata:
            return False
        
        processed_date = self.document_metadata[doc_key].get('processed_at', '')
        return processed_date == modified_date
    
    def _load_document_metadata(self) -> Dict:
        """Load document metadata from cache"""
        try:
            if self.document_cache_path.exists():
                with open(self.document_cache_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load document metadata: {e}")
        
        return {}
    
    def _save_document_metadata(self) -> None:
        """Save document metadata to cache"""
        try:
            with open(self.document_cache_path, 'w') as f:
                json.dump(self.document_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save document metadata: {e}")