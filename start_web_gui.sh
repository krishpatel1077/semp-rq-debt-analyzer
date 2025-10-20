#!/bin/bash
# Start the SEMP Requirements Debt Analyzer Web GUI

echo "🚀 Starting SEMP Requirements Debt Analyzer Web GUI..."
echo "================================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run 'python -m venv venv' first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if required packages are installed
python -c "import flask" 2>/dev/null || {
    echo "📦 Installing required packages..."
    pip install flask flask-cors
}

# Check if environment file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please configure your environment variables."
    echo "💡 Copy .env.example to .env and update the values."
    exit 1
fi

# Start the web application
echo "🌐 Starting web server on http://localhost:5000"
echo "🔄 The application will reload automatically when you make changes."
echo "⏹️  Press Ctrl+C to stop the server"
echo ""

python web_app.py