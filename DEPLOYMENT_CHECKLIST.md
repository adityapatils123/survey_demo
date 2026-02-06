# Deployment Checklist

Use this checklist to ensure a successful deployment.

## Pre-Deployment

- [ ] All code changes committed and tested locally
- [ ] `GEMINI_API_KEY` is available and valid
- [ ] All required files are present:
  - [ ] `Dockerfile`
  - [ ] `.dockerignore`
  - [ ] `requirements.txt`
  - [ ] `main.py`
  - [ ] `database.py`
  - [ ] `retry_utils.py`
  - [ ] `form_agent/` directory with all files
  - [ ] `static/` directory with all files

## Local Docker Testing

- [ ] Docker image builds successfully: `docker build -t survey-demo:test .`
- [ ] Container runs without errors: `docker run -p 7860:7860 -e GEMINI_API_KEY=test_key survey-demo:test`
- [ ] Application is accessible at `http://localhost:7860`
- [ ] WebSocket connection works (check browser console)
- [ ] Database file is created: `survey_sessions.db`
- [ ] Logs show no critical errors

## Hugging Face Spaces Deployment

- [ ] Created a new Docker Space on Hugging Face
- [ ] All files uploaded to Space repository
- [ ] `GEMINI_API_KEY` set in Space settings (Variables and secrets)
- [ ] Space SDK is set to "Docker"
- [ ] Build completes successfully (check build logs)
- [ ] Application is accessible at Space URL
- [ ] WebSocket connection works
- [ ] Test form submission works
- [ ] Session persistence works (refresh page, data persists)

## Post-Deployment Verification

- [ ] Application loads without errors
- [ ] Form interface displays correctly
- [ ] Can submit answers
- [ ] Navigation between steps works
- [ ] WebSocket messages are received
- [ ] Database operations work (check logs)
- [ ] No memory leaks or performance issues
- [ ] Error handling works (test with invalid inputs)

## Troubleshooting

If deployment fails:

1. **Check Build Logs**
   - Look for dependency installation errors
   - Verify all files are present
   - Check for syntax errors

2. **Check Runtime Logs**
   - Verify `GEMINI_API_KEY` is set
   - Check for import errors
   - Look for database connection issues

3. **Check Application Logs**
   - Monitor Space logs in real-time
   - Look for WebSocket connection errors
   - Check for API authentication errors

4. **Common Issues**
   - Missing environment variables
   - Port conflicts (should use 7860)
   - File permissions
   - Database file location

## Rollback Plan

If deployment fails:

1. Revert to previous working version
2. Check git history for last working commit
3. Rebuild and redeploy
4. Verify all functionality works

## Monitoring

After successful deployment:

- [ ] Monitor application logs regularly
- [ ] Check database size and growth
- [ ] Monitor API usage and quotas
- [ ] Set up alerts for errors (if available)
- [ ] Track user sessions and usage patterns
