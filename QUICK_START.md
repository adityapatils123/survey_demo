# Quick Start Guide

## 🚀 Fastest Way to Deploy

### Option 1: Hugging Face Spaces (Recommended)

1. **Create Space**
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Select **Docker** SDK
   - Name it (e.g., "survey-demo")

2. **Upload Files**
   ```bash
   # Clone or upload all files to your Space
   # Make sure Dockerfile is in root directory
   ```

3. **Set API Key**
   - Space Settings → Variables and secrets
   - Add: `GEMINI_API_KEY` = `your_key_here`

4. **Deploy**
   - Hugging Face auto-builds and deploys
   - Wait 2-5 minutes
   - Access at: `https://your-username-space-name.hf.space`

### Option 2: Local Docker

```bash
# 1. Build
docker build -t survey-demo .

# 2. Run
docker run -d \
  --name survey-demo \
  -p 7860:7860 \
  -e GEMINI_API_KEY=your_key_here \
  survey-demo

# 3. Access
# Open http://localhost:7860
```

### Option 3: Docker Compose

```bash
# 1. Create .env file
echo "GEMINI_API_KEY=your_key_here" > .env

# 2. Start
docker-compose up -d

# 3. Access
# Open http://localhost:7860
```

## 📋 Requirements

- **GEMINI_API_KEY**: Required (get from https://makersuite.google.com/app/apikey)
- **Port**: 7860 (for Hugging Face) or any port (local)
- **Python**: 3.11+ (handled by Docker)

## ✅ Verify Deployment

1. Open the application URL
2. Check browser console (F12) for errors
3. Test form submission
4. Verify WebSocket connection (should see connection messages)

## 🐛 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails | Check `requirements.txt` and `Dockerfile` |
| App won't start | Verify `GEMINI_API_KEY` is set |
| WebSocket error | Check browser console, verify endpoint |
| Port in use | Change port in docker run command |

## 📚 More Information

- **Full Docker Guide**: See [README_DOCKER.md](README_DOCKER.md)
- **HF Spaces Guide**: See [README_HF.md](README_HF.md)
- **Deployment Checklist**: See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
