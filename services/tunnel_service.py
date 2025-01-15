import os
import subprocess
import logging
from pyngrok import ngrok
import time

class TunnelService:
    def __init__(self, port):
        self.port = port
        self.public_url = None
        self.logger = logging.getLogger(__name__)
        
    def cleanup_sessions(self):
        try:
            ngrok.kill()
            time.sleep(2)
        except Exception as e:
            self.logger.error(f"Failed to cleanup ngrok sessions: {str(e)}")
    
    def start_ngrok(self):
        try:
            # Cleanup existing sessions
            self.cleanup_sessions()
            
            # Configure ngrok
            ngrok.set_auth_token(os.getenv('NGROK_AUTH_TOKEN'))
            
            # Start single tunnel
            config = {
                "addr": str(self.port),
                "hostname": "noted-raptor-evident.ngrok-free.app"
            }
            tunnel = ngrok.connect(**config)
            self.public_url = tunnel.public_url
            self.logger.info(f"Ngrok tunnel established: {self.public_url}")
            return self.public_url
            
        except Exception as e:
            self.logger.error(f"Failed to start ngrok: {str(e)}")
            return None