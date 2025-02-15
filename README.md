# Timeless Architecture
## Rasku's Timeless Vision

<div align="center">
  <img src="timeless_ui/public/logo/timeless_logo-removebg.png" alt="Timeless Logo" height="150" />
</div>

---

Timeless Architecture is an AI-driven modular meeting assistant designed to streamline software development discussions. It seamlessly integrates multiple services—including real-time voice transcription, AI-powered meeting management, and a live dashboard—to ensure project discussions are effectively captured, processed, and acted upon.

---

## Overview

Timeless Architecture consists of several key components:

- **Manager Service**: Handles meeting state transitions, processes transcriptions using LLMs, and initiates code generation when required.
- **Requirements Service**: Dynamically updates project requirements based on meeting transcriptions to ensure comprehensive tracking of evolving software needs.
- **Transcription Service**: Provides real-time speech-to-text functionality with support for local transcription models (faster-whisper) and cloud-based APIs, configurable for CPU or GPU acceleration.
- **Timeless UI**: A Next.js-powered frontend that offers a live dashboard with real-time updates on meeting discussions, project requirements, and current development state via Server-Sent Events (SSE).
- **Bootstrap Script**: The `bootstrap.py` script simplifies setup by creating a virtual environment, installing dependencies, and launching all core services.

---

## Features

- **Modular Multi-Service Architecture**: Each service runs independently, allowing easy customization and scalability.
- **Real-Time Transcription**: Captures and processes voice input with customizable transcription methods.
- **AI-Powered Meeting Management**: Utilizes LLMs (OpenAI, OpenRouter, or Ollama) for summarizing discussions, updating meeting notebooks, and triggering code generation.
- **Live Dashboard**: Displays meeting summaries, project states, and requirements in real time using SSE.
- **Flexible Configuration**: Easily switch between different LLM providers and transcription methods using environment variables.
- **Robust API-Driven Communication**: Services interact through REST APIs for smooth data exchange and integration.

---

## Installation

### Prerequisites

- **Python 3.8+**
- **Node.js** (required for Timeless UI)
- **Virtual environment tool** (recommended)

### Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/koodattu-varjotimeless-sjk.git
   cd koodattu-varjotimeless-sjk
   ```

2. **Create and Activate a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Bootstrap Script**
   ```bash
   python bootstrap.py
   ```
   Use `--cpu` or `--gpu` to specify Whisper transcription mode.

---

## Configuration

Create an `.env` file in the root directory and configure your settings:

```
# Service Ports
MANAGER_SERVICE_PORT=8082
REQUIREMENTS_SERVICE_PORT=8081
TRANSCRIPTION_SERVICE_PORT=8080

# LLM Provider (choose from: openrouter, openai, ollama)
LLM_PROVIDER=ollama

# API Keys and Model Configurations
OPENROUTER_API_KEY=your-openrouter-key
OPENAI_API_KEY=your-openai-key
OLLAMA_URL=http://localhost:11434/v1

# Transcription Configuration
TRANSCRIPTION_METHOD=local
TASK=translate
LOCAL_MODEL_SIZE=medium
USE_CUDA=True
AUDIO_DEVICE_INDEX=1
```

---

## Usage

Start the assistant with:

```bash
python main.py
```

If using WhatsApp integration, link your account using the QR code provided by Neonize in the console.

---

## API Services

### **Manager Service API**
- Handles meeting transcription processing, state transitions, and triggers code generation.
- Provides a **Server-Sent Events (SSE)** stream for real-time meeting updates.

### **Requirements Service API**
- Stores meeting discussions and updates software requirements dynamically.
- Provides an API to retrieve the latest requirements list for a given meeting.

### **Transcription Service API**
- Captures live audio, transcribes it using Whisper, and sends results to the manager service.
- Supports both local (faster-whisper) and cloud-based transcription (OpenAI Whisper API).

---

## File Structure

```
koodattu-varjotimeless-sjk/
├── bootstrap.py        # Sets up environment and starts services
├── example.env         # Sample environment configuration
├── requirements.txt    # Python dependencies
├── docs/               # API documentation for services
├── manager_service/    # Manages meeting state and discussions
├── requirements_service/ # Manages evolving project requirements
├── timeless_ui/        # Next.js frontend dashboard
└── transcription_service/ # Voice transcription and processing
```

---

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m "Add feature"`
4. Push to the branch: `git push origin feature-name`
5. Open a Pull Request.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Contact

For questions or support, open an issue or reach out to Juha Ala-Rantala at [juha.ala-rantala@tuni.fi](mailto:juha.ala-rantala@tuni.fi).
