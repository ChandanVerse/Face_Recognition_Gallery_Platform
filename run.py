"""
Backend startup script - Start FastAPI server
Run this from the project root directory
"""
import subprocess
import sys
import os
from pathlib import Path

def print_banner():
    """Print startup banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║          Face Recognition Gallery Platform               ║
    ║                   Backend Launcher                        ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_redis():
    """Check if Redis is running"""
    print("[CHECK] Checking Redis connection...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("[OK] Redis is running!")
        return True
    except Exception as e:
        print(f"[ERROR] Redis is not running. Please start Redis first:")
        print("   Windows: redis-server")
        print("   Linux/Mac: redis-server")
        return False

def check_mongodb():
    """Check if MongoDB connection string is configured"""
    print("\n[CHECK] Checking MongoDB configuration...")
    try:
        from backend.config.settings import get_settings
        settings = get_settings()
        if settings.MONGODB_URI and "mongodb" in settings.MONGODB_URI:
            print(f"[OK] MongoDB URI configured: {settings.MONGODB_DB_NAME}")
            return True
        else:
            print("[ERROR] MongoDB URI not configured properly in .env")
            return False
    except Exception as e:
        print(f"[ERROR] Error checking MongoDB config: {e}")
        return False

def check_storage():
    """Ensure storage directory exists"""
    print("\n[CHECK] Checking local storage...")
    storage_path = Path("storage")
    storage_path.mkdir(exist_ok=True)
    (storage_path / "galleries").mkdir(exist_ok=True)
    (storage_path / "reference").mkdir(exist_ok=True)
    print("[OK] Storage directories ready!")
    return True

def start_fastapi():
    """Start FastAPI server"""
    print("\n[START] Starting FastAPI server...")

    fastapi_cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", "7008",
        "--ssl-keyfile", "certs/key.pem",
        "--ssl-certfile", "certs/cert.pem",
        "--reload"
    ]

    print("\n" + "="*60)
    print("[OK] FastAPI Backend Starting...")
    print("="*60)
    print(f"[OK] API URL: https://recommendations.vosmos.events:7008")
    print(f"[OK] API Docs: https://recommendations.vosmos.events:7008/docs")
    print(f"[OK] Health Check: https://recommendations.vosmos.events:7008/health")
    print("="*60)
    print("\n[INFO] Remember to run in separate terminals:")
    print("   Terminal 1 (Celery): python backend/start_celery.py")
    print("   Terminal 3 (Frontend): npm run dev")
    print("="*60)
    print("\n[INFO] Press Ctrl+C to stop FastAPI\n")

    try:
        # Run FastAPI from project root
        subprocess.run(fastapi_cmd)
    except KeyboardInterrupt:
        print("\n\n[STOP] FastAPI server stopped.")
    except Exception as e:
        print(f"[ERROR] Error starting FastAPI: {e}")
        sys.exit(1)

def main():
    """Main startup function"""
    print_banner()

    # Ensure we're in the project root
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # Pre-flight checks
    checks_passed = True

    if not check_redis():
        checks_passed = False

    if not check_mongodb():
        checks_passed = False

    if not check_storage():
        checks_passed = False

    if not checks_passed:
        print("\n[ERROR] Pre-flight checks failed. Please fix the issues above.")
        sys.exit(1)

    print("\n[OK] All pre-flight checks passed!")
    print("\n" + "="*60)

    # Start FastAPI server
    start_fastapi()

if __name__ == "__main__":
    main()
