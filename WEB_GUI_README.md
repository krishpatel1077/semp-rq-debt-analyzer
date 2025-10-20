# SEMP Requirements Debt Analyzer - Web GUI

A local web-based interface for analyzing SEMP (Systems Engineering Management Plan) documents for requirements debt issues.

## Features

### Document Analysis
- **Upload Support**: Drag & drop or click to upload PDF, DOCX, TXT, and Markdown files (up to 50MB)
- **Real-time Analysis**: Advanced AI-powered analysis using AWS Bedrock (Claude 3 Haiku)
- **Coordinate-based Locations**: Precise text positioning with clickable location links
- **Severity Filtering**: Configurable severity thresholds (Low, Medium, High, Critical)

### Interactive Results Display
- **Detailed Issue Cards**: Each debt issue shows problem description, recommended fix, severity, and confidence
- **Clickable Locations**: Click on any location to view the exact text passage with highlighting
- **Export Functionality**: Download results as structured Markdown files
- **Visual Summary**: Statistics cards showing total issues, high-severity count, analysis time, and confidence

### AI Assistant Chat
- **Contextual Help**: Ask questions about specific analysis results
- **Deep-dive Reasoning**: Get detailed explanations about debt issues and recommended solutions
- **General Q&A**: Ask about requirements debt concepts and best practices
- **Session Persistence**: Chat history maintained during your session

### Modern Interface
- **Responsive Design**: Works on desktop and mobile devices
- **Bootstrap 5 UI**: Clean, professional appearance
- **Real-time Status**: Visual indicators for system status and operation progress
- **Drag & Drop**: Intuitive file upload experience

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ with virtual environment
- AWS credentials configured
- `.env` file with required environment variables

### Starting the Web GUI

1. **Easy Start** (recommended):
   ```bash
   ./start_web_gui.sh
   ```

2. **Manual Start**:
   ```bash
   source venv/bin/activate
   pip install flask flask-cors  # if not already installed
   python web_app.py
   ```

3. **Access the Application**:
   - Open your browser and go to: `http://localhost:5000`
   - The server runs on all interfaces (0.0.0.0:5000) for network access

## Usage Guide

### 1. Upload Document
- Click the upload area or drag & drop your SEMP document
- Supported formats: `.pdf`, `.docx`, `.txt`, `.md`
- Maximum file size: 50MB

### 2. Configure Analysis
- **Severity Threshold**: Choose minimum severity level to report
- **Include Suggestions**: Toggle improvement recommendations on/off

### 3. Run Analysis
- Click "Analyze Document"
- Wait for processing (typically 10-60 seconds depending on document size)
- View results in the analysis section

### 4. Explore Results
- **Click Location Links**: View exact text passages where issues occur
- **Ask AI Questions**: Use the "Ask AI About This" buttons for detailed explanations
- **Export Results**: Download structured Markdown report

### 5. Chat with AI Assistant
- Ask about specific issues: *"Can you explain more about this ambiguity issue?"*
- General questions: *"What are the best practices for requirements traceability?"*
- Get detailed reasoning: *"Why is this considered a critical issue?"*

## Technical Implementation

### Architecture
- **Backend**: Flask web server with REST API endpoints
- **Frontend**: Modern HTML5/CSS3/JavaScript with Bootstrap 5
- **Document Processing**: Coordinate-based text extraction and positioning
- **AI Integration**: AWS Bedrock for analysis and chat functionality
- **Storage**: Temporary file handling with session-based state management

### Key Components
- **Document Processor**: Enhanced text extraction with precise coordinate tracking
- **Debt Analyzer**: AI-powered requirements debt detection with location mapping
- **Chat System**: Contextual AI assistant for detailed explanations
- **Web Interface**: Responsive UI with real-time interactions

### Coordinate System
The application uses a sophisticated coordinate system to pinpoint exact text locations:
- **Character-based Positioning**: Precise start/end character positions
- **Line/Page Tracking**: Line numbers and page breaks for navigation
- **Context Extraction**: Surrounding text for highlighting and display
- **Interactive Display**: Clickable locations show exact problematic text

### API Endpoints
- `POST /upload` - Document upload
- `POST /analyze/<upload_id>` - Run analysis
- `POST /get_text_chunk` - Retrieve text with coordinates
- `POST /chat` - AI assistant interactions

## Deployment

### Local Development
The current setup is optimized for local development with Flask's built-in server.

### Production Deployment (EC2/Cloud)
For production deployment to EC2 or other cloud instances:

1. **Use Production WSGI Server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 web_app:app
   ```

2. **Environment Configuration**:
   - Set `FLASK_ENV=production` in .env
   - Configure proper AWS IAM roles for EC2
   - Set up SSL/HTTPS with reverse proxy (nginx)

3. **Security Considerations**:
   - Update `SECRET_KEY` for production
   - Configure CORS for your domain
   - Set up proper firewall rules
   - Consider file upload limits and storage

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "web_app:app"]
```

## Troubleshooting

### Common Issues

**"Virtual environment not found"**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**"AWS credentials not found"**
- Configure AWS CLI: `aws configure`
- Or set environment variables in `.env`

**"Session cookie too large" warning**
- This is normal for large analysis results
- Results are still saved correctly

**Analysis taking too long**
- Large documents (>100 pages) may take several minutes
- Check AWS Bedrock quota and region availability

### Performance Tips
- Use smaller documents for testing
- Lower severity thresholds reduce processing time
- Close browser tabs to free memory during analysis

## Features Comparison

| Feature | CLI Version | Web GUI |
|---------|-------------|---------|
| Document Upload | File path | Drag & drop |
| Analysis Results | Terminal table | Interactive cards |
| Location Info | Text description | Clickable coordinates |
| Export | Markdown file | Download button |
| Chat Support | Basic CLI chat | Full AI assistant |
| User Experience | Command line | Modern web interface |

## Future Enhancements

- **Multi-document Analysis**: Compare multiple SEMPs
- **Advanced Filtering**: Filter by debt type, confidence, section
- **Collaboration Features**: Share results and annotations
- **Report Templates**: Customizable output formats
- **Integration APIs**: Connect with project management tools
- **User Authentication**: Multi-user support with accounts

## Support

For issues or questions:
1. Check the console logs in your browser (F12 → Console)
2. Review the server terminal output for error details
3. Verify AWS credentials and service availability
4. Ensure all dependencies are installed correctly

The web GUI provides a comprehensive, user-friendly interface for requirements debt analysis with advanced AI assistance and precise location tracking.