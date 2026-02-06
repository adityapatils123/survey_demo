# Survey Demo - Hugging Face Spaces Quick Start

This is a quick deployment guide specifically for Hugging Face Spaces.

## Quick Setup

1. **Create a Docker Space**
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Select **Docker** as the SDK
   - Name your space

2. **Upload Files**
   - Upload all files from this repository to your Space
   - Ensure `Dockerfile` is in the root directory

3. **Set API Key**
   - Go to Space Settings → Variables and secrets
   - Add variable: `GEMINI_API_KEY` = `your_api_key_here`

4. **Deploy**
   - Hugging Face will automatically build and deploy
   - Wait for build to complete (usually 2-5 minutes)
   - Your app will be live at: `https://your-username-space-name.hf.space`

## Required Files for HF Spaces

Make sure these files are in your Space repository:

```
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── main.py
├── database.py
├── retry_utils.py
├── form_agent/
│   ├── __init__.py
│   ├── agent.py
│   └── survey_data.py
└── static/
    ├── form.html
    └── js/
        ├── form-app.js
        ├── audio-player.js
        ├── audio-recorder.js
        ├── pcm-player-processor.js
        └── pcm-recorder-processor.js
```

## Environment Variables

The Space automatically sets:
- `PORT=7860` (required by Hugging Face Spaces)

You must set:
- `GEMINI_API_KEY` (in Space settings)

## Troubleshooting

**Build fails?**
- Check that `Dockerfile` is in the root
- Verify all dependencies in `requirements.txt` are valid
- Check build logs in Space interface

**App doesn't start?**
- Verify `GEMINI_API_KEY` is set correctly
- Check application logs in Space interface
- Ensure port 7860 is exposed in Dockerfile

**WebSocket not working?**
- Hugging Face Spaces supports WebSockets
- Check browser console for connection errors
- Verify the WebSocket endpoint path is correct

## Notes

- The database (`survey_sessions.db`) is stored in the container
- Data persists during the Space session but may be reset on rebuild
- For persistent storage, consider using Hugging Face datasets or external storage
