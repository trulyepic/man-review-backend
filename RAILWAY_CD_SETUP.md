# Railway CD Visibility Setup

Railway publishes deployment status events back to GitHub when the backend is connected through Railway's GitHub integration. This repo listens for those GitHub `deployment_status` events and shows a separate `Railway Deployment Status` workflow in GitHub Actions.

## Required Setup

No GitHub secrets or repository variables are required for this phase.

Confirm these are true in Railway:

1. The backend service is connected to the GitHub repo.
2. GitHub autodeploys are enabled for `main`.
3. Railway sends deployment status events back to GitHub through its GitHub integration.

## What You Should See

After a merge to `main`:

1. The normal `Backend CI` workflow runs.
2. Railway deploys the backend through its GitHub integration.
3. GitHub receives Railway deployment status events.
4. The `Railway Deployment Status` workflow appears in GitHub Actions and shows:
   - ref
   - environment
   - state
   - description
   - deployment URL

If Railway reports a `failure` or `error` deployment state, the workflow fails so the problem is visible in GitHub.

## Notes

- This workflow does not trigger a Railway deployment.
- Railway remains responsible for deploying the backend.
- GitHub Actions only mirrors Railway's deployment result into the Actions UI.
