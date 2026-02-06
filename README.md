---
title: Survey Demo - Medical Survey Form
emoji: 📝
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# Survey Demo - Medical Survey Form Application

An intelligent voice and text-based survey form application built with Google ADK (Agent Development Kit) and FastAPI.

---

## 🚀 Live Deployment

This application is deployed using **Hugging Face Docker Spaces**.

### Required Environment Variable (Hugging Face Settings → Secrets):




# Survey Demo - Medical Survey Form Application

An intelligent voice and text-based survey form application built with Google ADK (Agent Development Kit) and FastAPI.

## Features

- Interactive survey form with voice and text support
- Session persistence using SQLite database
- WebSocket-based real-time communication
- Intelligent form assistant powered by Google Gemini
- Robust error handling with retry logic

## Quick Start

### Prerequisites

- Python 3.11+
- Google Gemini API Key
- Docker (for containerized deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "Survey Demo"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

5. **Run the application**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

6. **Access the application**
   Open your browser and navigate to `http://localhost:8000`

## Docker Deployment

### Quick Start with Docker

1. **Build the image**
   ```bash
   docker build -t survey-demo:latest .
   ```

2. **Run the container**
   ```bash
   docker run -d \
     --name survey-demo \
     -p 7860:7860 \
     -e GEMINI_API_KEY=your_api_key_here \
     survey-demo:latest
   ```

### Using Docker Compose

1. **Create `.env` file**
   ```
   GEMINI_API_KEY=your_api_key_here
   PORT=7860
   ```

2. **Start the service**
   ```bash
   docker-compose up -d
   ```

3. **View logs**
   ```bash
   docker-compose logs -f
   ```

For detailed Docker deployment instructions, see [README_DOCKER.md](README_DOCKER.md)

## Hugging Face Spaces Deployment

For deploying to Hugging Face Spaces, see [README_HF.md](README_HF.md)

### Quick Steps:
1. Create a Docker Space on Hugging Face
2. Upload all project files
3. Set `GEMINI_API_KEY` in Space settings
4. Deploy!

## Project Structure

```
.
├── main.py                 # FastAPI application entry point
├── database.py             # SQLite database module
├── retry_utils.py          # Retry utilities
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker Compose configuration
├── form_agent/            # Form agent module
│   ├── __init__.py
│   ├── agent.py           # Agent logic
│   └── survey_data.py     # Survey data and validation
└── static/                # Static files
    ├── form.html          # Main form interface
    └── js/                # JavaScript files
        ├── form-app.js
        ├── audio-player.js
        ├── audio-recorder.js
        ├── pcm-player-processor.js
        └── pcm-recorder-processor.js
```

## API Endpoints

### HTTP Endpoints

- `GET /` - Main form interface
- `GET /form` - Form page
- `GET /api/survey-data` - Get survey data structure
- `GET /api/session/{user_id}` - Get session data
- `POST /api/submit-answer` - Submit and validate answer

### WebSocket Endpoints

- `WS /ws/form/{user_id}?is_audio=false` - Form assistant WebSocket connection

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes | - |
| `PORT` | Server port | No | 7860 (Docker) / 8000 (local) |
| `HOST` | Server host | No | 0.0.0.0 |

## Database

The application uses SQLite for session persistence. The database file (`survey_sessions.db`) is created automatically on first run.

### Database Schema

- **sessions**: Stores user session data
- **session_history**: Audit trail of session actions

## Development

### Running Tests

```bash
# Install test dependencies (if any)
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Code Style

The project follows PEP 8 style guidelines. Consider using:
- `black` for code formatting
- `flake8` for linting
- `mypy` for type checking

## Troubleshooting

### Common Issues

1. **API Key Error**
   - Ensure `GEMINI_API_KEY` is set correctly
   - Check environment variables are loaded

2. **Database Errors**
   - Ensure write permissions in the application directory
   - Check database file isn't locked by another process

3. **WebSocket Connection Issues**
   - Verify WebSocket endpoint is accessible
   - Check browser console for errors
   - Ensure CORS is properly configured

4. **Port Already in Use**
   - Change the port in the command: `--port 8001`
   - Or set `PORT` environment variable

## License

Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Support

For issues or questions:
1. Check the application logs
2. Review the documentation files
3. Check GitHub issues (if applicable)

-----------