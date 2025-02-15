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

def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap the application: create venv, install requirements, and start all services."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--cpu", action="store_true", help="Install faster-whisper for CPU-only support.")
    group.add_argument("--gpu", action="store_true", help="Install faster-whisper and CUDA-enabled PyTorch for GPU support.")
    args = parser.parse_args()

    venv_dir = "venv"
    create_venv(venv_dir)
    python_path = get_venv_paths(venv_dir)
    install_requirements(python_path, args)
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
        print("All services have been terminated.")

if __name__ == "__main__":
    main()
