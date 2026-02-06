# Survey Demo - Docker Deployment Guide

This guide explains how to dockerize and deploy the Survey Demo application, including deployment to Hugging Face Spaces.

## Prerequisites

- Docker installed on your system
- For Hugging Face Spaces: A Hugging Face account

## Project Structure

```
.
├── Dockerfile              # Docker image definition
├── .dockerignore          # Files to exclude from Docker build
├── requirements.txt       # Python dependencies
├── main.py               # FastAPI application entry point
├── database.py           # SQLite database module
├── retry_utils.py        # Retry utilities
├── form_agent/           # Form agent module
│   ├── __init__.py
│   ├── agent.py
│   └── survey_data.py
└── static/               # Static files (HTML, JS)
    ├── form.html
    └── js/
```

## Environment Variables

The application requires the following environment variable:

- `GEMINI_API_KEY`: Your Google Gemini API key (required)

Optional environment variables:
- `PORT`: Port to run the server on (default: 7860 for Hugging Face Spaces)
- `HOST`: Host to bind to (default: 0.0.0.0)

## Local Docker Deployment

### 1. Build the Docker Image

```bash
docker build -t survey-demo:latest .
```

### 2. Run the Container

```bash
docker run -d \
  --name survey-demo \
  -p 7860:7860 \
  -e GEMINI_API_KEY=your_api_key_here \
  -v survey_data:/app/data \
  survey-demo:latest
```

The application will be available at `http://localhost:7860`

### 3. Using Docker Compose (Optional)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  survey-demo:
    build: .
    ports:
      - "7860:7860"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - PORT=7860
      - HOST=0.0.0.0
    volumes:
      - survey_data:/app/data
    restart: unless-stopped

volumes:
  survey_data:
```

Then run:
```bash
docker-compose up -d
```

## Hugging Face Spaces Deployment

### Method 1: Using Docker Space

1. **Create a new Space on Hugging Face**
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Select "Docker" as the SDK
   - Name your space (e.g., "survey-demo")

2. **Upload your files**
   - Upload all project files to the Space repository
   - Make sure to include:
     - `Dockerfile`
     - `.dockerignore`
     - `requirements.txt`
     - All Python files (`main.py`, `database.py`, `retry_utils.py`)
     - `form_agent/` directory
     - `static/` directory

3. **Set Environment Variables**
   - Go to your Space settings
   - Navigate to "Variables and secrets"
   - Add `GEMINI_API_KEY` with your API key value
   - The `PORT` variable is automatically set by Hugging Face (7860)

4. **Deploy**
   - Hugging Face will automatically build and deploy your Docker image
   - Monitor the build logs in the Space interface
   - Once deployed, your app will be available at `https://your-username-survey-demo.hf.space`

### Method 2: Using Git Repository

1. **Push to Git Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://huggingface.co/spaces/your-username/survey-demo
   git push -u origin main
   ```

2. **Configure Space**
   - Set the Space SDK to "Docker"
   - Add `GEMINI_API_KEY` in Space settings

## Verifying Deployment

1. **Check Health**
   - Visit `http://localhost:7860/` (local) or your Space URL
   - You should see the survey form interface

2. **Check Logs**
   ```bash
   # Local Docker
   docker logs survey-demo
   
   # Or follow logs
   docker logs -f survey-demo
   ```

3. **Test WebSocket Connection**
   - Open the form in a browser
   - Check browser console for WebSocket connection status
   - The WebSocket endpoint is at `/ws/form/{user_id}`

## Troubleshooting

### Port Issues
- Ensure the `PORT` environment variable matches the exposed port in Dockerfile
- For Hugging Face Spaces, use port 7860

### Database Issues
- The SQLite database file (`survey_sessions.db`) will be created automatically
- For persistent storage, use Docker volumes (local) or Space storage (Hugging Face)

### API Key Issues
- Ensure `GEMINI_API_KEY` is set correctly
- Check logs for authentication errors

### Build Failures
- Check Docker build logs for dependency issues
- Ensure all files are included (check `.dockerignore`)

### WebSocket Connection Issues
- Verify the WebSocket endpoint is accessible
- Check browser console for connection errors
- Ensure CORS is properly configured (FastAPI handles this automatically)

## Development Workflow

### Local Development with Docker

1. **Make changes to code**
2. **Rebuild image**
   ```bash
   docker build -t survey-demo:latest .
   ```
3. **Restart container**
   ```bash
   docker restart survey-demo
   ```

### Testing Before Deployment

```bash
# Build and run locally first
docker build -t survey-demo:test .
docker run -p 7860:7860 -e GEMINI_API_KEY=your_key survey-demo:test

# Test the application
curl http://localhost:7860/
```

## Production Considerations

1. **Security**
   - Never commit `.env` files or API keys
   - Use environment variables for sensitive data
   - Enable HTTPS in production (Hugging Face Spaces provides this automatically)

2. **Performance**
   - Database file is stored in container (consider external database for production)
   - Monitor resource usage in Hugging Face Spaces

3. **Scaling**
   - For multiple instances, consider external database (PostgreSQL, etc.)
   - Current SQLite setup works for single-instance deployments

4. **Monitoring**
   - Check Hugging Face Spaces logs regularly
   - Monitor database size and performance

## Additional Resources

- [Hugging Face Spaces Documentation](https://huggingface.co/docs/hub/spaces)
- [Docker Documentation](https://docs.docker.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## Support

For issues or questions:
1. Check the application logs
2. Review this documentation
3. Check Hugging Face Spaces community forums
