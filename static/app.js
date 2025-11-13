/**
 * SEMP Requirements Debt Analyzer - Web Application
 */

class SEMPAnalyzer {
    constructor() {
        this.uploadId = null;
        this.analysisId = null;
        this.chatSessionId = null;
        this.analysisResults = null;
        
        this.initializeEventListeners();
        this.updateStatus('ready', 'Ready for analysis');
    }
    
    initializeEventListeners() {
        // File upload events
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const analyzeBtn = document.getElementById('analyzeBtn');
        
        // Upload area click
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFile(files[0]);
            }
        });
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFile(e.target.files[0]);
            }
        });
        
        // Analyze button
        analyzeBtn.addEventListener('click', () => {
            this.analyzeDocument();
        });
        
        // Chat events
        const chatInput = document.getElementById('chatInput');
        const sendChatBtn = document.getElementById('sendChatBtn');
        
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendChatMessage();
            }
        });
        
        sendChatBtn.addEventListener('click', () => {
            this.sendChatMessage();
        });
        
        // Export button
        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportResults();
        });
    }
    
    updateStatus(type, message) {
        const indicator = document.querySelector('.status-indicator');
        const statusText = indicator.nextElementSibling;
        
        indicator.className = `status-indicator status-${type}`;
        statusText.textContent = message;
    }
    
    async handleFile(file) {
        // Validate file type
        const allowedTypes = ['.pdf', '.docx', '.txt', '.md'];
        const fileExt = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(fileExt)) {
            this.showAlert('Error', `File type ${fileExt} is not supported. Please use: ${allowedTypes.join(', ')}`);
            return;
        }
        
        // Validate file size (50MB)
        if (file.size > 50 * 1024 * 1024) {
            this.showAlert('Error', 'File size must be less than 50MB');
            return;
        }
        
        // Update UI
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('fileSize').textContent = this.formatFileSize(file.size);
        document.getElementById('fileInfo').style.display = 'block';
        document.getElementById('analysisSettings').style.display = 'block';
        
        // Upload file
        try {
            this.updateStatus('processing', 'Uploading file...');
            
            const formData = new FormData();
            formData.append('document', file);
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.uploadId = result.upload_id;
                this.updateStatus('ready', 'File uploaded - ready to analyze');
                document.getElementById('analyzeBtn').disabled = false;
            } else {
                this.showAlert('Upload Error', result.error);
                this.updateStatus('error', 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showAlert('Upload Error', 'Failed to upload file. Please try again.');
            this.updateStatus('error', 'Upload failed');
        }
    }
    
    async analyzeDocument() {
        if (!this.uploadId) {
            this.showAlert('Error', 'Please upload a file first');
            return;
        }
        
        const analyzeBtn = document.getElementById('analyzeBtn');
        const loadingSpinner = analyzeBtn.querySelector('.loading');
        const btnIcon = analyzeBtn.querySelector('.fas');
        
        try {
            // Update UI
            analyzeBtn.disabled = true;
            loadingSpinner.style.display = 'inline-block';
            btnIcon.style.display = 'none';
            this.updateStatus('processing', 'Analyzing document...');
            
            // Get analysis settings
            const severityThreshold = document.getElementById('severityThreshold').value;
            const includeSuggestions = document.getElementById('includeSuggestions').checked;
            
            const response = await fetch(`/analyze/${this.uploadId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    severity_threshold: severityThreshold,
                    include_suggestions: includeSuggestions
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.analysisId = result.analysis_id;
                this.analysisResults = result.result;
                this.displayAnalysisResults(result.result);
                this.updateStatus('ready', 'Analysis complete');
                document.getElementById('exportBtn').disabled = false;
            } else {
                this.showAlert('Analysis Error', result.error);
                this.updateStatus('error', 'Analysis failed');
            }
        } catch (error) {
            console.error('Analysis error:', error);
            this.showAlert('Analysis Error', 'Failed to analyze document. Please try again.');
            this.updateStatus('error', 'Analysis failed');
        } finally {
            // Reset button
            analyzeBtn.disabled = false;
            loadingSpinner.style.display = 'none';
            btnIcon.style.display = 'inline';
        }
    }
    
    displayAnalysisResults(results) {
        const container = document.getElementById('analysisResults');
        
        if (!results.issues || results.issues.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-check-circle fa-2x mb-3 text-success"></i>
                    <h5>No Issues Found</h5>
                    <p>Great! No requirements debt issues were detected in this document.</p>
                </div>
            `;
            return;
        }
        
        // Summary section
        let html = `
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-center" style="border-top: 3px solid var(--draper-orange);">
                        <div class="card-body">
                            <h3 class="card-title" style="color: var(--draper-orange);">${results.total_issues}</h3>
                            <p class="card-text">Total Issues</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center" style="border-top: 3px solid var(--draper-black);">
                        <div class="card-body">
                            <h3 class="card-title" style="color: var(--draper-black);">${results.summary.high_severity_issues || 0}</h3>
                            <p class="card-text">High/Critical</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center" style="border-top: 3px solid var(--draper-orange-hover);">
                        <div class="card-body">
                            <h3 class="card-title" style="color: var(--draper-orange-hover);">${results.analysis_duration.toFixed(2)}s</h3>
                            <p class="card-text">Analysis Time</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center" style="border-top: 3px solid var(--draper-orange);">
                        <div class="card-body">
                            <h3 class="card-title" style="color: var(--draper-orange);">${(results.summary.average_confidence * 100).toFixed(0)}%</h3>
                            <p class="card-text">Avg Confidence</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <h6 class="mb-3">Issues Found:</h6>
        `;
        
        // Issues list
        results.issues.forEach((issue, index) => {
            const severityClass = this.getSeverityClass(issue.severity);
            const coordinates = this.parseCoordinates(issue.location_in_text);
            
            html += `
                <div class="debt-issue" data-issue-index="${index}">
                    <div class="row">
                        <div class="col-md-8">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <span class="badge ${severityClass} severity-badge">${issue.severity}</span>
                                <span class="badge bg-secondary">${issue.debt_type}</span>
                            </div>
                            
                            <h6 class="mb-2">Problem:</h6>
                            <p class="mb-2">${this.escapeHtml(issue.problem_description)}</p>
                            
                            ${issue.recommended_fix ? `
                                <h6 class="mb-2">Recommended Fix:</h6>
                                <p class="mb-2 text-success">${this.escapeHtml(issue.recommended_fix)}</p>
                            ` : ''}
                            
                            <small class="text-muted">
                                <strong>Reference:</strong> ${this.escapeHtml(issue.reference)}<br>
                                <strong>Confidence:</strong> ${(issue.confidence * 100).toFixed(0)}%
                            </small>
                        </div>
                        
                        <div class="col-md-4">
                            <h6 class="mb-2">Location:</h6>
                            <div class="location-link" data-coordinates='${JSON.stringify(coordinates)}' onclick="app.showTextLocation(this)">
                                <i class="fas fa-map-marker-alt me-1"></i>
                                ${this.escapeHtml(this.cleanLocationText(issue.location_in_text))}
                            </div>
                            
                            <div class="mt-3">
                                <button class="btn btn-sm btn-outline-primary" onclick="app.askAboutIssue(${index})">
                                    <i class="fas fa-question-circle me-1"></i>
                                    Ask AI About This
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }
    
    parseCoordinates(locationText) {
        // Try to extract coordinates from the location text
        const match = locationText.match(/\[COORDS:(.+?)\]/);
        if (match) {
            try {
                return JSON.parse(match[1]);
            } catch (e) {
                console.warn('Failed to parse coordinates:', e);
            }
        }
        return null;
    }
    
    cleanLocationText(locationText) {
        // Remove coordinate information from display text
        return locationText.replace(/\[COORDS:.+?\]$/, '').trim();
    }
    
    async showTextLocation(element) {
        const coordinatesData = element.getAttribute('data-coordinates');
        
        if (!coordinatesData || coordinatesData === 'null') {
            this.showAlert('Info', 'Precise location coordinates not available for this issue.');
            return;
        }
        
        try {
            const coordinates = JSON.parse(coordinatesData);
            
            // Get the text chunk from the server
            const response = await fetch('/get_text_chunk', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    analysis_id: this.analysisId,
                    chunk_start: Math.max(0, coordinates.char_start - 200),
                    chunk_end: coordinates.char_end + 200
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Show in modal with highlighting
                const textViewerContent = document.getElementById('textViewerContent');
                const textChunk = result.text_chunk;
                
                // Calculate relative positions within the chunk
                const relativeStart = coordinates.char_start - result.chunk_start;
                const relativeEnd = coordinates.char_end - result.chunk_start;
                
                // Highlight the relevant text
                const beforeText = textChunk.substring(0, Math.max(0, relativeStart));
                const highlightText = textChunk.substring(Math.max(0, relativeStart), relativeEnd);
                const afterText = textChunk.substring(relativeEnd);
                
                textViewerContent.innerHTML = `
                    ${this.escapeHtml(beforeText)}<span class="highlighted-text">${this.escapeHtml(highlightText)}</span>${this.escapeHtml(afterText)}
                `;
                
                // Show modal
                const modal = new bootstrap.Modal(document.getElementById('textViewerModal'));
                modal.show();
            } else {
                this.showAlert('Error', 'Failed to retrieve text location: ' + result.error);
            }
        } catch (error) {
            console.error('Error showing text location:', error);
            this.showAlert('Error', 'Failed to show text location');
        }
    }
    
    askAboutIssue(issueIndex) {
        if (!this.analysisResults || !this.analysisResults.issues[issueIndex]) {
            return;
        }
        
        const issue = this.analysisResults.issues[issueIndex];
        const question = `Can you explain more about this ${issue.debt_type} issue: "${issue.problem_description}"? What makes this problematic and how should it be addressed?`;
        
        // Set the question in the chat input
        document.getElementById('chatInput').value = question;
        
        // Scroll to chat section
        document.getElementById('chatInput').scrollIntoView({ behavior: 'smooth' });
        
        // Focus on input
        document.getElementById('chatInput').focus();
    }
    
    async sendChatMessage() {
        const chatInput = document.getElementById('chatInput');
        const sendChatBtn = document.getElementById('sendChatBtn');
        const message = chatInput.value.trim();
        
        if (!message) return;
        
        // Clear input and disable button
        chatInput.value = '';
        chatInput.disabled = true;
        sendChatBtn.disabled = true;
        
        // Add user message to chat
        this.addChatMessage(message, 'user');
        
        // Add thinking indicator
        const thinkingId = this.addThinkingIndicator();
        
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    analysis_id: this.analysisId,
                    chat_session_id: this.chatSessionId
                })
            });
            
            const result = await response.json();
            
            // Remove thinking indicator
            this.removeThinkingIndicator(thinkingId);
            
            if (result.success) {
                this.chatSessionId = result.chat_session_id;
                this.addChatMessage(result.response, 'assistant');
            } else {
                this.addChatMessage('Sorry, I encountered an error processing your message: ' + result.error, 'assistant');
            }
        } catch (error) {
            console.error('Chat error:', error);
            this.removeThinkingIndicator(thinkingId);
            this.addChatMessage('Sorry, I encountered an error connecting to the AI service.', 'assistant');
        } finally {
            // Re-enable input
            chatInput.disabled = false;
            sendChatBtn.disabled = false;
            chatInput.focus();
        }
    }
    
    addThinkingIndicator() {
        const chatMessages = document.getElementById('chatMessages');
        const thinkingDiv = document.createElement('div');
        const thinkingId = 'thinking-' + Date.now();
        thinkingDiv.id = thinkingId;
        thinkingDiv.className = 'message assistant';
        thinkingDiv.innerHTML = `
            <strong>AI Assistant:</strong>
            <div class="d-flex align-items-center">
                <div class="spinner-border spinner-border-sm me-2" role="status" style="color: var(--draper-orange);">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <span class="text-muted">Thinking...</span>
            </div>
        `;
        chatMessages.appendChild(thinkingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return thinkingId;
    }
    
    removeThinkingIndicator(thinkingId) {
        const thinkingDiv = document.getElementById(thinkingId);
        if (thinkingDiv) {
            thinkingDiv.remove();
        }
    }
    
    addChatMessage(message, sender) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        if (sender === 'user') {
            messageDiv.innerHTML = `<strong>You:</strong><p class="mb-0">${this.escapeHtml(message)}</p>`;
        } else {
            // Render markdown for assistant messages
            const renderedMarkdown = marked.parse(message);
            messageDiv.innerHTML = `<strong>AI Assistant:</strong><div class="markdown-content">${renderedMarkdown}</div>`;
        }
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    exportResults() {
        if (!this.analysisResults) {
            this.showAlert('Error', 'No analysis results to export');
            return;
        }
        
        // Create markdown content
        let markdown = `# SEMP Requirements Debt Analysis Results\n\n`;
        markdown += `**Document:** ${this.analysisResults.document_name}\n`;
        markdown += `**Analysis Date:** ${this.analysisResults.analysis_timestamp}\n`;
        markdown += `**Total Issues:** ${this.analysisResults.total_issues}\n`;
        markdown += `**Analysis Duration:** ${this.analysisResults.analysis_duration.toFixed(2)} seconds\n\n`;
        
        markdown += `## Summary\n\n`;
        markdown += `- **High/Critical Issues:** ${this.analysisResults.summary.high_severity_issues || 0}\n`;
        markdown += `- **Average Confidence:** ${(this.analysisResults.summary.average_confidence * 100).toFixed(0)}%\n`;
        markdown += `- **Most Common Debt Type:** ${this.analysisResults.summary.most_common_debt_type || 'N/A'}\n\n`;
        
        markdown += `## Issues Found\n\n`;
        
        this.analysisResults.issues.forEach((issue, index) => {
            markdown += `### Issue ${index + 1}: ${issue.debt_type}\n\n`;
            markdown += `**Location:** ${this.cleanLocationText(issue.location_in_text)}\n\n`;
            markdown += `**Severity:** ${issue.severity}\n\n`;
            markdown += `**Problem:** ${issue.problem_description}\n\n`;
            
            if (issue.recommended_fix) {
                markdown += `**Recommended Fix:** ${issue.recommended_fix}\n\n`;
            }
            
            markdown += `**Reference:** ${issue.reference}\n\n`;
            markdown += `**Confidence:** ${(issue.confidence * 100).toFixed(0)}%\n\n`;
            markdown += `---\n\n`;
        });
        
        // Download the file
        const blob = new Blob([markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.analysisResults.document_name}_analysis_results.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    getSeverityClass(severity) {
        const classes = {
            'Low': 'bg-secondary',
            'Medium': 'text-white',
            'High': 'text-white',
            'Critical': 'text-white'
        };
        
        // Use inline styles for Draper colors since CSS variables aren't available in JS
        const severityElement = classes[severity] || 'bg-secondary';
        
        switch(severity) {
            case 'Medium':
                return severityElement + '" style="background-color: var(--draper-orange-hover);';
            case 'High':
                return severityElement + '" style="background-color: var(--draper-orange);';
            case 'Critical':
                return severityElement + '" style="background-color: var(--draper-black);';
            default:
                return 'bg-secondary';
        }
    }
    
    formatFileSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showAlert(title, message) {
        // Simple alert for now - could be enhanced with a better modal system
        alert(`${title}: ${message}`);
    }
}

// Initialize the application
const app = new SEMPAnalyzer();