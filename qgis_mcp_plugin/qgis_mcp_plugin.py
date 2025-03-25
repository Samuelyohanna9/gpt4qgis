import os
import json
import socket
import traceback
from qgis.core import *
from qgis.gui import *
from qgis.PyQt.QtCore import QObject, pyqtSignal, QTimer, Qt, QSize
from qgis.PyQt.QtWidgets import (QAction, QDockWidget, QVBoxLayout, 
                                QLabel, QPushButton, QSpinBox, QWidget)
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.utils import active_plugins

class QgisMCPServer(QObject):
    """Server class to handle socket connections"""
    def __init__(self, host='localhost', port=9876, iface=None):
        super().__init__()
        self.host = host
        self.port = port
        self.iface = iface
        self.running = False
        self.socket = None
        self.client = None
        self.buffer = b''
        self.timer = None
    
    def start(self):
        """Start the server"""
        try:
            self.running = True
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.socket.setblocking(False)
            
            self.timer = QTimer()
            self.timer.timeout.connect(self.process_server)
            self.timer.start(100)
            
            QgsMessageLog.logMessage(f"Server started on {self.host}:{self.port}", "QGIS MCP")
            return True
        except Exception as e:
            QgsMessageLog.logMessage(f"Failed to start server: {str(e)}", "QGIS MCP", Qgis.Critical)
            self.stop()
            return False
            
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.timer:
            self.timer.stop()
        if self.socket:
            self.socket.close()
        if self.client:
            self.client.close()
        QgsMessageLog.logMessage("Server stopped", "QGIS MCP")
    
    def process_server(self):
        """Handle incoming connections"""
        if not self.running:
            return
            
        try:
            # Accept new connection
            if not self.client:
                try:
                    self.client, addr = self.socket.accept()
                    self.client.setblocking(False)
                    QgsMessageLog.logMessage(f"Client connected: {addr}", "QGIS MCP")
                except BlockingIOError:
                    pass
                except Exception as e:
                    QgsMessageLog.logMessage(f"Connection error: {str(e)}", "QGIS MCP", Qgis.Warning)
            
            # Process client
            if self.client:
                try:
                    data = self.client.recv(8192)
                    if data:
                        self.buffer += data
                        try:
                            command = json.loads(self.buffer.decode('utf-8'))
                            self.buffer = b''
                            QgsMessageLog.logMessage(f"Received command: {command}", "QGIS MCP")
                            response = self.execute_command(command)
                            self.client.sendall(json.dumps(response).encode('utf-8'))
                        except json.JSONDecodeError:
                            pass
                    else:
                        self.client.close()
                        self.client = None
                        self.buffer = b''
                except BlockingIOError:
                    pass
                except Exception as e:
                    QgsMessageLog.logMessage(f"Client error: {str(e)}", "QGIS MCP", Qgis.Warning)
                    self.client.close()
                    self.client = None
                    self.buffer = b''
                    
        except Exception as e:
            QgsMessageLog.logMessage(f"Server error: {str(e)}", "QGIS MCP", Qgis.Critical)

    def execute_command(self, command):
        """Execute QGIS commands"""
        try:
            cmd = command.get("type")
            params = command.get("params", {})
            
            # Clean None values from params
            params = {k: v for k, v in params.items() if v is not None}
            
            QgsMessageLog.logMessage(f"Executing {cmd} with {params}", "QGIS MCP")
            
            if cmd == "create_new_project":
                return self.create_project(params.get("path"))
            elif cmd == "add_vector_layer":
                return self.add_vector_layer(
                    params.get("path"),
                    params.get("provider", "ogr"),
                    params.get("name")
                )
            elif cmd == "add_raster_layer":
                return self.add_raster_layer(
                    params.get("path"),
                    params.get("provider", "gdal"),
                    params.get("name")
                )
            elif cmd == "load_project":
                return self.load_project(params.get("path"))
            elif cmd == "save_project":
                return self.save_project(params.get("path"))
            elif cmd == "get_layers":
                return self.get_layers()
            elif cmd == "remove_layer":
                return self.remove_layer(params.get("layer_id"))
            elif cmd == "zoom_to_layer":
                return self.zoom_to_layer(params.get("layer_id"))
            elif cmd == "get_layer_features":
                return self.get_layer_features(
                    params.get("layer_id"),
                    params.get("limit", 10)
                )
            elif cmd == "execute_processing":
                return self.execute_processing(
                    params.get("algorithm"),
                    params.get("parameters", {})
                )
            elif cmd == "render_map":
                return self.render_map(
                    params.get("path"),
                    params.get("width", 800),
                    params.get("height", 600)
                )
            elif cmd == "execute_code":
                return self.execute_code(params.get("code"))
            elif cmd == "get_qgis_info":
                return self.get_qgis_info()
            elif cmd == "ping":
                return {"status": "success", "result": {"pong": True}}
            else:
                return {"status": "error", "message": f"Unknown command: {cmd}"}
                
        except Exception as e:
            QgsMessageLog.logMessage(f"Command error: {traceback.format_exc()}", "QGIS MCP", Qgis.Critical)
            return {"status": "error", "message": str(e)}
    
    def create_project(self, path):
        try:
            project = QgsProject.instance()
            project.clear()
            project.setFileName(path)
            if project.write():
                return {
                    "status": "success",
                    "result": {
                        "created": f"Project created and saved successfully at: {path}",
                        "layer_count": len(project.mapLayers())
                    }
                }
            return {
                "status": "error",
                "message": project.error()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def add_vector_layer(self, path, provider="ogr", name=None):
        try:
            if not name:
                name = os.path.splitext(os.path.basename(path))[0]
            
            layer = QgsVectorLayer(path, name, provider)
            if not layer.isValid():
                return {"status": "error", "message": f"Invalid layer: {path}"}
            
            QgsProject.instance().addMapLayer(layer)
            return {
                "status": "success",
                "layer": name,
                "layer_id": layer.id()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def add_raster_layer(self, path, provider="gdal", name=None):
        try:
            if not name:
                name = os.path.splitext(os.path.basename(path))[0]
            
            layer = QgsRasterLayer(path, name, provider)
            if not layer.isValid():
                return {"status": "error", "message": f"Invalid layer: {path}"}
            
            QgsProject.instance().addMapLayer(layer)
            return {
                "status": "success",
                "layer": name,
                "layer_id": layer.id()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def load_project(self, path):
        try:
            project = QgsProject.instance()
            if project.read(path):
                return {
                    "status": "success",
                    "result": {
                        "loaded": f"Project loaded from: {path}",
                        "layer_count": len(project.mapLayers())
                    }
                }
            return {
                "status": "error",
                "message": project.error()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def save_project(self, path):
        try:
            project = QgsProject.instance()
            project.setFileName(path)
            if project.write():
                return {
                    "status": "success",
                    "result": {
                        "saved": f"Project saved to: {path}",
                        "layer_count": len(project.mapLayers())
                    }
                }
            return {
                "status": "error",
                "message": project.error()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_layers(self):
        try:
            layers = QgsProject.instance().mapLayers()
            return {
                "status": "success",
                "result": {
                    "layers": [
                        {
                            "id": layer.id(),
                            "name": layer.name(),
                            "type": layer.type().name,
                            "crs": layer.crs().authid()
                        }
                        for layer in layers.values()
                    ]
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def remove_layer(self, layer_id):
        try:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                QgsProject.instance().removeMapLayer(layer_id)
                return {
                    "status": "success",
                    "result": f"Layer {layer_id} removed"
                }
            return {
                "status": "error",
                "message": f"Layer {layer_id} not found"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def zoom_to_layer(self, layer_id):
        try:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer:
                self.iface.mapCanvas().setExtent(layer.extent())
                self.iface.mapCanvas().refresh()
                return {
                    "status": "success",
                    "result": f"Zoomed to layer {layer_id}"
                }
            return {
                "status": "error",
                "message": f"Layer {layer_id} not found"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_layer_features(self, layer_id, limit=10):
        try:
            layer = QgsProject.instance().mapLayer(layer_id)
            if not layer or not isinstance(layer, QgsVectorLayer):
                return {
                    "status": "error",
                    "message": f"Vector layer {layer_id} not found"
                }
            
            features = []
            for i, feature in enumerate(layer.getFeatures()):
                if i >= limit:
                    break
                features.append(feature.attributes())
            
            return {
                "status": "success",
                "result": {
                    "layer": layer.name(),
                    "features": features,
                    "count": len(features)
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def execute_processing(self, algorithm, parameters):
        try:
            result = processing.run(algorithm, parameters)
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def render_map(self, path, width=800, height=600):
        try:
            settings = self.iface.mapCanvas().mapSettings()
            settings.setOutputSize(QSize(width, height))
            
            image = QImage(settings.outputSize(), QImage.Format_ARGB32)
            image.fill(Qt.white)
            
            painter = QPainter(image)
            settings.setOutputDpi(96)
            mapRenderer = QgsMapRendererCustomPainterJob(settings, painter)
            mapRenderer.start()
            mapRenderer.waitForFinished()
            painter.end()
            
            image.save(path)
            return {
                "status": "success",
                "result": {
                    "saved": f"Map image saved to: {path}",
                    "dimensions": f"{width}x{height}"
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def execute_code(self, code):
        try:
            # Security note: In production, this should have proper sandboxing
            locals_dict = {}
            exec(code, {"qgis": qgis, "QgsProject": QgsProject}, locals_dict)
            return {
                "status": "success",
                "result": locals_dict.get("result", "Code executed")
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_qgis_info(self):
        try:
            return {
                "status": "success",
                "result": {
                    "version": Qgis.QGIS_VERSION,
                    "plugins": active_plugins()
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

class QgisMCPDockWidget(QDockWidget):
    """Dock widget for UI"""
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("QGIS MCP Server")
        self.setup_ui()
        
    def setup_ui(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Server not running")
        self.toggle_button = QPushButton("Start Server")
        self.toggle_button.clicked.connect(self.toggle_server)
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(9876)
        
        layout.addWidget(QLabel("Port:"))
        layout.addWidget(self.port_input)
        layout.addWidget(self.status_label)
        layout.addWidget(self.toggle_button)
        widget.setLayout(layout)
        self.setWidget(widget)
        
    def toggle_server(self):
        if hasattr(self, 'server') and self.server.running:
            self.server.stop()
            self.status_label.setText("Server stopped")
            self.toggle_button.setText("Start Server")
        else:
            self.server = QgisMCPServer(
                iface=self.iface,
                port=self.port_input.value()
            )
            if self.server.start():
                self.status_label.setText(f"Server running on port {self.server.port}")
                self.toggle_button.setText("Stop Server")
            else:
                self.status_label.setText("Failed to start server")

class QgisMCPPlugin:
    """Main plugin class"""
    def __init__(self, iface):
        self.iface = iface
        self.dock_widget = None
        
    def initGui(self):
        self.dock_widget = QgisMCPDockWidget(self.iface)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        
    def unload(self):
        if self.dock_widget:
            if hasattr(self.dock_widget, 'server'):
                self.dock_widget.server.stop()
            self.iface.removeDockWidget(self.dock_widget)

def classFactory(iface):
    return QgisMCPPlugin(iface)