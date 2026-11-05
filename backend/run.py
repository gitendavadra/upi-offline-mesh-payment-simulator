import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app import create_app

env = os.environ.get('FLASK_ENV', 'development')
app = create_app(env)

if __name__ == '__main__':
    # Prioritize FLASK_PORT or BACKEND_PORT to avoid container-level PORT=8080 collisions
    port = int(os.environ.get('FLASK_PORT') or os.environ.get('BACKEND_PORT') or 5001)
    print(f"🚀 Starting UPI Offline Mesh Payment Simulator on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)

