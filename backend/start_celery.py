"""
Celery Worker Startup Script
Run this in a separate terminal to see Celery task logs
"""
import subprocess
import sys
import signal
from pathlib import Path

# Add parent directory to Python path so imports work
backend_dir = Path(__file__).parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

# Global variable to store the Celery process
celery_process = None

def print_banner():
    """Print startup banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║              🔧 Celery Worker Launcher 🔧                ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global celery_process
    print("\n\n🛑 Shutting down Celery worker...")
    print("⏳ Please wait while tasks complete gracefully...")

    if celery_process:
        # Send SIGTERM for graceful shutdown
        celery_process.terminate()
        try:
            # Wait up to 10 seconds for graceful shutdown
            celery_process.wait(timeout=10)
            print("✅ Celery worker stopped gracefully")
        except subprocess.TimeoutExpired:
            # Force kill if it takes too long
            print("⚠️  Forcing shutdown...")
            celery_process.kill()
            celery_process.wait()
            print("✅ Celery worker stopped (forced)")

    sys.exit(0)

def get_optimal_concurrency():
    """Determine optimal concurrency based on platform and CPU cores"""
    import os

    # Check for environment variable override
    env_concurrency = os.getenv("CELERY_CONCURRENCY")
    if env_concurrency:
        try:
            return int(env_concurrency)
        except ValueError:
            pass

    # GPU workload optimization - limit to 2 concurrent tasks
    # This prevents GPU memory overload during face recognition
    return 2

def main():
    """Start Celery worker"""
    global celery_process

    print_banner()

    print("📊 Starting Celery Worker...")
    print("=" * 60)
    print("💡 Make sure you have started:")
    print("   - Redis server")
    print("   - FastAPI backend (run.py in another terminal)")
    print("=" * 60)
    print("\n")

    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)

    # Get optimal concurrency
    concurrency = get_optimal_concurrency()

    # Determine platform-specific settings
    if sys.platform == "win32":
        # Windows uses gevent pool (lightweight greenlets)
        pool_type = "gevent"
        print(f"🔧 Platform: Windows")
        print(f"🔧 Pool: {pool_type} (greenlet-based, good for I/O + CPU tasks)")
        print(f"🔧 Concurrency: {concurrency} concurrent tasks")
        print(f"💡 Tip: Install gevent if not already: pip install gevent")

        celery_cmd = [
            sys.executable, "-m", "celery",
            "-A", "backend.workers.celery_app",
            "worker",
            "--loglevel=info",
            "--pool=gevent",
            f"--concurrency={concurrency}"
        ]
    else:
        # Linux/Mac uses prefork pool (multi-process)
        pool_type = "prefork"
        print(f"🔧 Platform: Linux/Mac")
        print(f"🔧 Pool: {pool_type} (multi-process, best for CPU tasks)")
        print(f"🔧 Max workers: 3 processes")
        print(f"🔧 Concurrency per worker: {concurrency} tasks")
        print(f"🔧 Total concurrent tasks: 3 x {concurrency} = {3 * concurrency}")

        celery_cmd = [
            sys.executable, "-m", "celery",
            "-A", "backend.workers.celery_app",
            "worker",
            "--loglevel=info",
            f"--concurrency={concurrency}",
            "--autoscale=3,2"  # Max 3 worker processes, min 2
        ]

    print("\n" + "=" * 60)
    print("🚀 Starting worker...")
    print("=" * 60)
    print("💡 Press Ctrl+C to stop (graceful shutdown with 10s timeout)")
    print("=" * 60)
    print("\n")

    try:
        # Use Popen instead of run for better process control
        celery_process = subprocess.Popen(celery_cmd, cwd=project_root)

        # Wait for process to complete
        celery_process.wait()

    except Exception as e:
        print(f"❌ Error starting Celery: {e}")
        if celery_process:
            celery_process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()
