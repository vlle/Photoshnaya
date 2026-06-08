# Deploy Helper

Small local Go HTTP tool for collecting the GitHub deploy secrets and values used by `.github/workflows/python-app.yml`.

## Run

```bash
cd deploy-helper
go run .
```

Then open `http://127.0.0.1:8091`.

The page defaults to the current production target: `root@157.22.182.58`.

## What It Helps With

- reads the default image repository from `../docker-compose.yml`
- generates `DEPLOY_KNOWN_HOSTS` with `ssh-keyscan`
- validates remote SSH access and deploy path with `ssh`
- scans local `~/.ssh` keys and can reveal a selected private key locally for `DEPLOY_SSH_KEY`
- probes common remote directories for candidate deploy paths
- shows all GitHub secrets in one place

## What Still Must Be Provided Manually

- `DOCKERHUB_TOKEN` still has to be created in Docker Hub, but the helper links to the correct page
