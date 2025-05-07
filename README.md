A bridge between QGIS and AI capabilities, enabling natural language commands for geospatial workflows.

## Features

- 🗣️ Natural language processing for QGIS commands
- 🔌 Real-time connection to QGIS via TCP socket
- 🤖 OpenAI integration for command interpretation
- 📜 Chat history with context preservation
- 📊 Status monitoring of QGIS/LLM connections

## Installation

### Prerequisites
- QGIS 3.28+
- Python 3.9+
- OpenAI API key

### 1. QGIS Plugin Installation
```bash
# Clone the repository
git clone https://github.com/Samuelyohanna9/gpt4qgis.git

# Install the plugin
cp -r qgis_mcp_plugin/ ~/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/
2. Python Server Setup
bash
cd qgis_mcp_server
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.\.venv\Scripts\activate   # Windows

pip install -r requirements.txt

# Configure environment
echo "OPENAI_API_KEY=your_api_key_here" > .env
Usage
Start QGIS and enable the plugin:

Go to Plugins → Manage and Install Plugins

Search for "QGIS MCP" and enable it

Click "Start Server" in the dock widget

Run the backend server:

bash
python qgis_mcp_server.py
Launch the frontend:

bash
cd qgis-chat-frontend
npm install
npm start

Architecture





![20250507_899a81](https://github.com/user-attachments/assets/53538d51-f62f-4947-8c3b-072da0b00973)





Troubleshooting
Common Issues
Symptom	Solution
"No response from QGIS"	Verify plugin server is running in QGIS
Connection timeouts	Check firewall rules for port 9876
API key errors	Ensure .env contains valid OpenAI key
CORS errors	Verify Flask CORS configuration
Debugging Tools
powershell
# Test TCP connection manually
Test-NetConnection -ComputerName localhost -Port 9876

# Check running servers
Get-Process -Name "python","qgis" | Format-Table -AutoSize
Configuration
Backend Settings
Edit config.py:

python
QGIS_SERVER = {
    "host": "localhost",
    "port": 9876,
    "timeout": 10.0
}

OPENAI = {
    "model": "gpt-3.5-turbo",
    "temperature": 0.1
}
Frontend Customization
Edit src/config.js:

javascript
export const SERVER_URL = 'http://localhost:9876';
export const THEME = {
    primaryColor: '#2c3e50',
    secondaryColor: '#3498db'
};
Development
Running Tests
bash
# Backend tests
pytest tests/

# Frontend tests
cd qgis-chat-frontend
npm test
Building for Production
bash
cd qgis-chat-frontend
npm run build
