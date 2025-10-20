#!/usr/bin/env python3
"""
Flask Web Application for SEMP Requirements Debt Analyzer GUI
"""
import os
import sys
import json
import uuid
import subprocess
import tempfile
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from loguru import logger

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from config.settings import settings
from src.agent.session_manager import SEMPChatSessionManager
from src.agent.debt_analyzer import RequirementsDebtAnalyzer
from src.rag.knowledge_base import SEMPKnowledgeBase
from src.rag.document_processor import DocumentProcessor
from src.models.debt_models import AnalysisRequest, SeverityLevel

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', str(uuid.uuid4()))
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

CORS(app)

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

# Global components
knowledge_base = None
session_manager = None
document_processor = None

def initialize_components():
    """Initialize global components"""
    global knowledge_base, session_manager, document_processor
    try:
        knowledge_base = SEMPKnowledgeBase()
        session_manager = SEMPChatSessionManager()
        document_processor = DocumentProcessor()
        logger.info("Components initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        raise

@app.before_request
def startup():
    """Initialize components before first request"""
    if not hasattr(app, '_initialized'):
        initialize_components()
        app._initialized = True

@app.route('/')
def index():
    """Main page with document upload interface"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_document():
    """Handle document upload and return file info"""
    try:
        if 'document' not in request.files:
            return jsonify({'error': 'No document file provided'}), 400
        
        file = request.files['document']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'.pdf', '.docx', '.txt', '.md'}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'File type {file_ext} not supported. Allowed: {", ".join(allowed_extensions)}'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        upload_id = str(uuid.uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{upload_id}_{filename}")
        file.save(file_path)
        
        # Store file info in session
        session[upload_id] = {
            'filename': filename,
            'file_path': file_path,
            'upload_time': str(pd.Timestamp.now())
        }
        
        logger.info(f"Document uploaded: {filename} ({upload_id})")
        
        return jsonify({
            'success': True,
            'upload_id': upload_id,
            'filename': filename,
            'file_size': os.path.getsize(file_path)
        })
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/analyze/<upload_id>', methods=['POST'])
def analyze_document(upload_id):
    """Analyze uploaded document for requirements debt"""
    try:
        # Get file info from session
        if upload_id not in session:
            return jsonify({'error': 'Upload ID not found'}), 404
        
        file_info = session[upload_id]
        file_path = file_info['file_path']
        filename = file_info['filename']
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Uploaded file not found'}), 404
        
        # Get analysis parameters
        severity_threshold = request.json.get('severity_threshold', 'Low')
        include_suggestions = request.json.get('include_suggestions', True)
        
        # Extract text from document
        with open(file_path, 'rb') as f:
            binary_content = f.read()
        
        text_content = document_processor.extract_text(binary_content, filename)
        if not text_content:
            return jsonify({'error': 'Failed to extract text from document'}), 400
        
        # Create analysis request
        analysis_request = AnalysisRequest(
            document_content=text_content,
            document_name=filename,
            severity_threshold=SeverityLevel(severity_threshold),
            include_suggestions=include_suggestions
        )
        
        # Perform analysis with document processor
        analyzer = RequirementsDebtAnalyzer(knowledge_base, document_processor)
        result = analyzer.analyze_document(analysis_request)
        
        # Convert result to dict for JSON serialization
        result_dict = result.dict()
        
        # Store analysis result in session for later retrieval
        session[f"{upload_id}_analysis"] = result_dict
        
        logger.info(f"Analysis completed for {filename}: {result.total_issues} issues found")
        
        return jsonify({
            'success': True,
            'analysis_id': f"{upload_id}_analysis",
            'result': result_dict
        })
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_text_chunk', methods=['POST'])
def get_text_chunk():
    """Get specific text chunk for location highlighting"""
    try:
        analysis_id = request.json.get('analysis_id')
        chunk_start = request.json.get('chunk_start', 0)
        chunk_end = request.json.get('chunk_end', 200)
        
        if not analysis_id or analysis_id not in session:
            return jsonify({'error': 'Analysis ID not found'}), 404
        
        # Extract original upload_id from analysis_id
        upload_id = analysis_id.replace('_analysis', '')
        if upload_id not in session:
            return jsonify({'error': 'Upload ID not found'}), 404
        
        file_info = session[upload_id]
        file_path = file_info['file_path']
        filename = file_info['filename']
        
        # Re-extract text to get the exact chunk
        with open(file_path, 'rb') as f:
            binary_content = f.read()
        
        text_content = document_processor.extract_text(binary_content, filename)
        
        # Extract the requested chunk
        text_chunk = text_content[chunk_start:chunk_end] if text_content else ""
        
        return jsonify({
            'success': True,
            'text_chunk': text_chunk,
            'chunk_start': chunk_start,
            'chunk_end': chunk_end
        })
        
    except Exception as e:
        logger.error(f"Failed to get text chunk: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """Handle chat interactions for deep-dive analysis"""
    try:
        message = request.json.get('message')
        analysis_id = request.json.get('analysis_id')
        chat_session_id = request.json.get('chat_session_id')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Create new chat session if not provided
        if not chat_session_id:
            chat_session_id = session_manager.create_session('web_user')
            if not chat_session_id:
                return jsonify({'error': 'Failed to create chat session'}), 500
        
        # Store analysis context in DynamoDB for session manager access
        if analysis_id and analysis_id in session:
            analysis_result = session[analysis_id]
            # Store the analysis in DynamoDB so session manager can access it
            session_manager.db_client.store_agent_info(
                f"session_analysis_{chat_session_id}",
                {
                    "current_document": analysis_result.get('document_name', 'unknown'),
                    "last_analysis": analysis_result,
                    "analysis_timestamp": analysis_result.get('analysis_timestamp', '')
                }
            )
            
            # Create detailed context message with specific issue information
            issues = analysis_result.get('issues', [])
            if issues:
                # Find if the message relates to a specific issue
                context_details = []
                for issue in issues:
                    issue_description = issue.get('problem_description', '')
                    issue_type = issue.get('debt_type', '')
                    if (any(word in message.lower() for word in issue_description.lower().split()[:3]) or 
                        issue_type.lower() in message.lower()):
                        context_details.append({
                            'type': issue_type,
                            'problem': issue_description,
                            'location': issue.get('location_in_text', ''),
                            'fix': issue.get('recommended_fix', ''),
                            'severity': issue.get('severity', ''),
                            'confidence': issue.get('confidence', 0)
                        })
                
                if context_details:
                    # Format specific issue context
                    issue_context = "\n".join([
                        f"Issue: {detail['type']} (Severity: {detail['severity']})\n"
                        f"Problem: {detail['problem']}\n"
                        f"Location: {detail['location']}\n"
                        f"Recommended Fix: {detail['fix']}\n"
                        for detail in context_details[:2]  # Limit to 2 most relevant
                    ])
                    
                    context_message = f"""Based on the analysis results for {analysis_result.get('document_name', 'the document')} that found {analysis_result.get('total_issues', 0)} total issues, here are the relevant findings:

{issue_context}

User Question: {message}

Please provide a detailed explanation addressing the user's question about this specific issue."""
                else:
                    # General analysis context
                    context_message = f"""Based on the analysis results for {analysis_result.get('document_name', 'the document')} that found {analysis_result.get('total_issues', 0)} issues with the following distribution:
{'; '.join([f"{k}: {v}" for k, v in analysis_result.get('severity_distribution', {}).items() if v > 0])}

User Question: {message}

Please answer the user's question in the context of this analysis."""
            else:
                context_message = message
        else:
            context_message = message
        
        # Process the message
        response = session_manager.process_user_message(chat_session_id, context_message)
        
        return jsonify({
            'success': True,
            'response': response,
            'chat_session_id': chat_session_id
        })
        
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({'error': 'File too large. Maximum size is 50MB'}), 413

@app.errorhandler(500)
def server_error(e):
    """Handle server errors"""
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Import pandas for timestamp (needed in upload function)
    import pandas as pd
    
    # Create templates and static directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("Starting SEMP Requirements Debt Analyzer Web Server...")
    print("Access the application at: http://localhost:5001")
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,
        threaded=True
    )
