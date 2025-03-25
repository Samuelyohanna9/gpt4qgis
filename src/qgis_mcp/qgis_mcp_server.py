#!/usr/bin/env python3
"""
QGIS MCP Server with LLM Integration and HTTP API
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import socket
import threading
import time
import json
import logging
import re
from typing import Dict, Any
from dotenv import load_dotenv, find_dotenv, set_key
import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("QgisGPTMCPServer")

app = Flask(__name__)
CORS(app)

class APIKeyManager:
    @staticmethod
    def get_key():
        """Secure API key handling with .env storage"""
        env_path = find_dotenv()
        if not env_path:
            env_path = os.path.join(os.path.expanduser("~"), ".env")
            open(env_path, 'a').close()
            
        load_dotenv(env_path)
        api_key = os.getenv('OPENAI_API_KEY')
        
        if api_key:
            return api_key
            
        print("\nAPI Key Required")
        print("1. Get your key from https://platform.openai.com/api-keys")
        print("2. The key starts with 'sk-'")
        
        while True:
            api_key = input("Enter OpenAI API Key: ").strip()
            if api_key.startswith("sk-"):
                set_key(env_path, "OPENAI_API_KEY", api_key)
                print(f"API key stored securely in {env_path}")
                return api_key
            print("Invalid API key format. Must start with 'sk-'. Try again.")

class QgisConnection:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        
    def connect(self):
        try:
            if self.socket:
                self.socket.close()
                
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info("Connected to QGIS plugin")
            return True
        except socket.timeout:
            logger.warning("Connection timed out - is QGIS plugin running?")
            self.connected = False
            return False
        except Exception as e:
            self.connected = False
            logger.error(f"Connection failed: {str(e)}", exc_info=True)
            return False

    def send_command(self, command: Dict[str, Any]):
        """Send command in plugin-compatible format"""
        if not self.connected and not self.connect():
            return {"status": "error", "message": "Not connected to QGIS"}
            
        try:
            plugin_command = {
                "type": command["command"],
                "params": command["params"]
            }
            
            if plugin_command["type"] == "create_project":
                plugin_command["type"] = "create_new_project"
            
            logger.info(f"Sending to plugin: {json.dumps(plugin_command, indent=2)}")
            self.socket.sendall(json.dumps(plugin_command).encode('utf-8'))
            
            response = b''
            while True:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    try:
                        return json.loads(response.decode('utf-8'))
                    except json.JSONDecodeError:
                        continue
                except socket.timeout:
                    break
                    
            if response:
                return json.loads(response.decode('utf-8'))
            return {"status": "error", "message": "No response from QGIS"}
        except Exception as e:
            logger.error(f"Command failed: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}

class QGISAutomation:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=APIKeyManager.get_key())
        self.qgis = QgisConnection()
        self.qgis.connect()  # Try initial connection but don't fail if it doesn't work

    def _extract_json(self, text: str):
        """Robust JSON extraction from text"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        raise ValueError("No valid JSON found in response")

    def process_request(self, prompt: str):
        """Process natural language prompt with LLM"""
        try:
            system_prompt = """You are a QGIS automation assistant. Respond ONLY with JSON:
            {
                "command": "create_project|add_vector_layer|add_raster_layer|load_project|save_project|get_layers|remove_layer|zoom_to_layer|get_layer_features|execute_processing|render_map|execute_code",
                "params": {
                    "path": "string",
                    "name": "string",
                    "provider": "string",
                    "layer_id": "string",
                    "limit": integer,
                    "algorithm": "string",
                    "parameters": {},
                    "width": integer,
                    "height": integer,
                    "code": "string"
                }
            }"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            command = self._extract_json(content)
            
            if not all(k in command for k in ["command", "params"]):
                raise ValueError("Missing required fields in command")
                
            logger.info(f"Executing command: {command}")
            return self.qgis.send_command(command)
            
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}

class SystemStatus:
    def __init__(self):
        self.automation = None
        self.current_directory = os.getcwd()
        self.last_activity = None
        self.running = True
        
        try:
            self.automation = QGISAutomation()
        except Exception as e:
            logger.error(f"Failed to initialize QGIS automation: {str(e)}", exc_info=True)

    def update_directory(self, path):
        if os.path.exists(path):
            self.current_directory = path
            return True
        return False

    def monitor_connection(self):
        while self.running:
            try:
                if not hasattr(self, 'automation') or not self.automation:
                    self.automation = QGISAutomation()
                elif not self.automation.qgis.connected:
                    self.automation.qgis.connect()
            except Exception as e:
                logger.warning(f"Connection attempt failed: {str(e)}")
            time.sleep(5)

status = SystemStatus()
threading.Thread(target=status.monitor_connection, daemon=True).start()

@app.route('/api/status', methods=['GET'])
def get_status():
    connected = hasattr(status, 'automation') and status.automation and status.automation.qgis.connected
    return jsonify({
        "qgis_connected": connected,
        "current_directory": status.current_directory,
        "last_activity": status.last_activity
    })

@app.route('/api/command', methods=['POST'])
def handle_command():
    if not hasattr(status, 'automation') or not status.automation:
        return jsonify({"status": "error", "message": "QGIS connection not available"}), 503
    
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"status": "error", "message": "Missing prompt"}), 400
    
    status.last_activity = time.strftime("%Y-%m-%d %H:%M:%S")
    result = status.automation.process_request(data['prompt'])
    
    if result.get('status') == 'success' and 'params' in result and 'path' in result['params']:
        status.update_directory(result['params']['path'])
    
    return jsonify(result)

@app.route('/api/llm_test', methods=['POST'])
def test_llm():
    data = request.get_json()
    try:
        test_prompt = data.get('prompt', 'Test connection')
        response = status.automation.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": test_prompt}],
            max_tokens=50
        )
        return jsonify({"status": "success", "response": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/check_connection', methods=['GET'])
def check_connection():
    if hasattr(status, 'automation') and status.automation:
        connected = status.automation.qgis.connect()  # Attempt reconnect
        return jsonify({"connected": connected})
    return jsonify({"connected": False})

if __name__ == "__main__":
    from waitress import serve
    logger.info("Starting QGIS MCP Server on port 9876")
    serve(app, host="0.0.0.0", port=9876)