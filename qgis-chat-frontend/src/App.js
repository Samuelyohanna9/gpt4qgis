import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { CheckCircle, XCircle, Folder, Send, RefreshCw, Cpu } from 'react-feather';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState('');
  const [status, setStatus] = useState({
    qgisConnected: false,
    currentDir: '',
    lastActivity: null,
    llmConnected: false,
    loading: false
  });

  // Check system status
  const checkStatus = async () => {
    try {
      const [statusRes, llmRes] = await Promise.all([
        axios.get('http://localhost:9876/api/status'),
        axios.post('http://localhost:9876/api/llm_test', { prompt: 'ping' })
      ]);
      
      setStatus(prev => ({
        ...prev,
        qgisConnected: statusRes.data.qgis_connected,
        currentDir: statusRes.data.current_directory,
        lastActivity: statusRes.data.last_activity,
        llmConnected: llmRes.data.status === 'success',
        loading: false
      }));
    } catch (err) {
      setStatus(prev => ({ ...prev, loading: false }));
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus(prev => ({ ...prev, loading: true }));
    
    try {
      const res = await axios.post('http://localhost:9876/api/command', { prompt });
      setResponse(JSON.stringify(res.data, null, 2));
      checkStatus(); // Refresh status after command
    } catch (err) {
      setResponse(`Error: ${err.message}`);
    } finally {
      setStatus(prev => ({ ...prev, loading: false }));
    }
  };

  return (
    <div className="app-container">
      <div className="status-bar">
        <div className="status-item">
          {status.qgisConnected ? (
            <CheckCircle color="#4CAF50" size={18} />
          ) : (
            <XCircle color="#F44336" size={18} />
          )}
          <span>QGIS {status.qgisConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
        
        <div className="status-item">
          {status.llmConnected ? (
            <CheckCircle color="#4CAF50" size={18} />
          ) : (
            <XCircle color="#F44336" size={18} />
          )}
          <span>LLM {status.llmConnected ? 'Ready' : 'Offline'}</span>
        </div>
        
        <div className="status-item">
          <Folder size={18} />
          <span>Directory: {status.currentDir || 'Not specified'}</span>
        </div>
      </div>

      <div className="command-interface">
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Tell QGIS what to do (e.g., 'Load the buildings layer from C:/data/buildings.shp')"
              disabled={status.loading}
            />
            <button type="submit" disabled={!prompt || status.loading}>
              {status.loading ? (
                <>
                  <RefreshCw className="spin" size={18} /> Processing...
                </>
              ) : (
                <>
                  <Send size={18} /> Execute
                </>
              )}
            </button>
          </div>
        </form>

        <div className="response-container">
          {status.lastActivity && (
            <div className="last-activity">
              Last action: {new Date(status.lastActivity).toLocaleString()}
            </div>
          )}
          <pre className="response">
            {response || 'Command results will appear here...'}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default App;