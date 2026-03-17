# Spiral Visualizer

This project is configured to deploy automatically to GitHub Pages.

## One-time GitHub setup

1. Push this repo to GitHub (branch: `main`).
2. In GitHub, open **Settings -> Pages**.
3. Set **Source** to **GitHub Actions**.

## Deploy

Every push to `main` triggers the workflow in `.github/workflows/deploy-pages.yml` and publishes:

- `index.html`
- `app.js`
- `styles.css`
- any other static files in the repo

Once the workflow finishes, the site URL is:

`https://<your-github-username>.github.io/<repo-name>/`
