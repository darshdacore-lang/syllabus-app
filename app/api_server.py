"""
HTTP API server for Electron IPC communication.
Runs as a background process spawned by Electron main.js.
Exposes Python backend via simple HTTP endpoints.
"""

import sys
import json
import logging
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import signal
from urllib.parse import urlparse, parse_qs
import traceback

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.data.storage import Storage
from app.core.session_engine import SessionEngine
from app.core.taskmanager import TaskManager
from app.data.agent import Agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


class APIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for API calls."""
    
    agent = None  # Set by server before running

    def do_POST(self):
        """Handle POST requests with JSON payload."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._send_json(400, {'success': False, 'error': 'Invalid JSON payload'})
                return
            
            path = urlparse(self.path).path
            command = payload.get('command')
            args = payload.get('args', {})
            
            logger.info(f"Command: {command}, Args: {args}")
            
            # Route to command handler
            if command:
                try:
                    result = self.agent.handle_command(command, **args) # type: ignore
                except ValueError as ve:
                    self._send_json(400, {'success': False, 'error': str(ve)})
                    return
                self._send_json(200, {'success': True, 'data': result})
            else:
                self._send_json(400, {'success': False, 'error': 'No command provided'})
                
        except Exception as e:
            logger.error(f"Error: {e}\n{traceback.format_exc()}")
            self._send_json(500, {'success': False, 'error': str(e)})

    def do_GET(self):
        """Handle GET requests for status and diagnostics."""
        path = urlparse(self.path).path
        
        if path == '/health':
            self._send_json(200, {'status': 'ok', 'version': '1.0.0'})
        elif path == '/commands':
            commands = list(self.agent.commands.keys())# type: ignore
            self._send_json(200, {'commands': commands})
        else:
            self._send_json(404, {'error': 'Not found'})

    def _send_json(self, status_code, data):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        payload = json.dumps(data).encode('utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass


def run_server(port=5555, data_path=None):
    """Start the API server."""
    try:
        # Initialize backend
        storage = Storage(path=data_path)
        session_engine = SessionEngine(storage)
        task_manager = TaskManager(storage)
        agent = Agent(session_engine, task_manager)
        
        APIHandler.agent = agent# type: ignore
        
        server = ThreadingHTTPServer(('localhost', port), APIHandler)
        logger.info(f"🚀 API server running on http://localhost:{port}")
        
        # Send ready signal to Electron
        print("READY", flush=True)
        # Handle termination signals gracefully so parent process can shutdown
        def _shutdown(signum, frame):
            logger.info(f"Received signal {signum}, shutting down server...")
            try:
                server.shutdown()
            except Exception:
                pass

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)
        
        server.serve_forever()
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5555
    data_path = sys.argv[2] if len(sys.argv) > 2 else None
    run_server(port, data_path)
