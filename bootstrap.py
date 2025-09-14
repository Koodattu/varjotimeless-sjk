import os
import sys
import subprocess
import time
import argparse

def create_venv(venv_dir="venv"):
    if not os.path.exists(venv_dir):
        print("Creating virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
    else:
        print("Virtual environment already exists.")

def get_venv_paths(venv_dir="venv"):
    if os.name == "nt":
        # Windows paths
        python_path = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        # macOS/Linux paths
        python_path = os.path.join(venv_dir, "bin", "python")
    return python_path

def install_requirements(python_path, args):
    # Upgrade pip using "python -m pip"
    print("Upgrading pip...")
    subprocess.check_call([python_path, "-m", "pip", "install", "--upgrade", "pip"])

    print("Installing base requirements from requirements.txt...")
    subprocess.check_call([python_path, "-m", "pip", "install", "-r", "requirements.txt"])

    # Optionally install additional packages for transcription
    if args.cpu:
        print("Installing faster-whisper for CPU support...")
        subprocess.check_call([python_path, "-m", "pip", "install", "faster-whisper"])
    elif args.gpu:
        print("Installing faster-whisper and CUDA-enabled PyTorch packages for GPU support...")
        subprocess.check_call([python_path, "-m", "pip", "install", "faster-whisper"])
        subprocess.check_call([
            python_path,
            "-m",
            "pip",
            "install",
            "torch",
            "torchaudio",
            "--extra-index-url",
            "https://download.pytorch.org/whl/cu118"
        ])

def start_services(python_path):
    services = [
        {"name": "Manager Service", "script": os.path.join("manager_service", "manager_service.py")},
        {"name": "Requirements Service", "script": os.path.join("requirements_service", "requirements_manager.py")},
        {"name": "Transcription Service", "script": os.path.join("transcription_service", "transcribe_service.py")}
    ]
    processes = []
    for service in services:
        print(f"Starting {service['name']}...")
        proc = subprocess.Popen([python_path, service["script"]])
        processes.append(proc)
    return processes

def npm_install_if_needed(ui_dir):
    node_modules = os.path.join(ui_dir, "node_modules")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    if not os.path.exists(node_modules):
        print("Running 'npm install' in timeless_ui (first time setup)...")
        subprocess.check_call([npm_cmd, "install"], cwd=ui_dir)
    else:
        print("'node_modules' already exists, skipping 'npm install'.")

def start_nextjs_dev(ui_dir):
    print("Starting Next.js dev server in timeless_ui...")
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    # Start as a background process
    proc = subprocess.Popen([npm_cmd, "run", "dev"], cwd=ui_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc

def wait_for_nextjs_ready(port=3000, timeout=60):
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("localhost", port), timeout=2):
                return True
        except Exception:
            time.sleep(1)
    return False

def open_browser(url):
    import webbrowser
    print(f"Opening browser at {url}")
    webbrowser.open(url)

def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap the application: create venv, install requirements, and start all services."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cpu", action="store_true", help="Install faster-whisper for CPU-only support.")
    group.add_argument("--gpu", action="store_true", help="Install faster-whisper and CUDA-enabled PyTorch for GPU support.")
    parser.add_argument("--web", action="store_true", help="Install and start the frontend (timeless_ui)")
    args = parser.parse_args()

    venv_dir = "venv"
    create_venv(venv_dir)
    python_path = get_venv_paths(venv_dir)
    install_requirements(python_path, args)

    timeless_ui_dir = os.path.join(os.path.dirname(__file__), "timeless_ui")
    nextjs_proc = None

    if args.web:
        # --- Frontend setup ---
        npm_install_if_needed(timeless_ui_dir)
        # Start Next.js dev server
        nextjs_proc = start_nextjs_dev(timeless_ui_dir)
        # Wait for Next.js to be ready, then open browser
        if wait_for_nextjs_ready():
            open_browser("http://localhost:3000")
        else:
            print("Warning: Next.js dev server did not start in time.")

    # Start backend services
    processes = start_services(python_path)

    print("All services are running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down services...")
        for proc in processes:
            proc.terminate()
        for proc in processes:
            proc.wait()
        print("All backend services have been terminated.")
        if nextjs_proc:
            print("Terminating Next.js dev server...")
            nextjs_proc.terminate()
            nextjs_proc.wait()
            print("Next.js dev server terminated.")

if __name__ == "__main__":
    main()
