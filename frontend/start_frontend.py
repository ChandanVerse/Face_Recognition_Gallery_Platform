"""
Frontend (React) Startup Script
Run this in a separate terminal to see frontend build logs
"""
import subprocess
import sys
from pathlib import Path

def print_banner():
    """Print startup banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║            ⚛️  React Frontend Launcher ⚛️                ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Start React development server (Vite)"""
    print_banner()

    print("📊 Starting React Frontend (Vite)...")
    print("=" * 60)
    print("💡 Make sure you have started:")
    print("   - FastAPI backend (run.py)")
    print("   - Celery worker (start_celery.py)")
    print("=" * 60)
    print("\n")

    frontend_dir = Path(__file__).parent

    try:
        # Run npm run dev (Vite uses 'dev' not 'start')
        if sys.platform == "win32":
            subprocess.run(["npm.cmd", "run", "dev"], cwd=frontend_dir, shell=True)
        else:
            subprocess.run(["npm", "run", "dev"], cwd=frontend_dir)
    except KeyboardInterrupt:
        print("\n\n🛑 Frontend server stopped.")
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
