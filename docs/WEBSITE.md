# Lost Meadows Project Website

This directory (`docs/`) contains the GitHub Pages website for the Lost Meadows
capstone project. It is a static multi-page site (plain HTML/CSS/JS, no build step
required) that is served directly by GitHub Pages.

**Live site:** https://raidersoft.github.io/Lost-Meadows/

## Pages

| File | Page |
|------|------|
| `index.html` | Home — project overview and entry point |
| `client.html` | Client & problem statement |
| `tools.html` | Tools & technologies used |
| `team.html` | Team member profiles |
| `video.html` | Project video |
| `download.html` | Data / limited-data download links |
| `dashboard.html` | Interactive watershed results dashboard (reads logs from `../GEE/TIF_Output/Logs/`) |

## Supporting Files

| File | Purpose |
|------|---------|
| `styles.css` | Site-wide stylesheet |
| `nav.js` | Sticky header + mobile nav toggle |
| `leaves.js`, `logo-animate.js`, `scroll-animate.js` | Decorative/scroll animations |
| `favicon.svg` | Site favicon |
| `_config.yml` | Jekyll/GitHub Pages configuration |
| `images/` | Team photos and other image assets |

## Deployment

The site is deployed with GitHub Pages from the `docs/` folder on the `main` branch:

1. Go to the repository **Settings → Pages**.
2. Under **Source**, select **Deploy from a branch**.
3. Choose the **main** branch and the **/docs** folder.
4. Click **Save**.

GitHub Pages publishes the site at `https://<username>.github.io/Lost-Meadows/`.
Changes pushed to `docs/` on `main` are published automatically within a minute or two.

## Local Development

Because the site is plain static HTML, you can preview it without Jekyll. From the
repository root:

```bash
cd docs
python -m http.server 8000
# then open http://localhost:8000 in your browser
```

If you want to reproduce the exact GitHub Pages (Jekyll) build instead:

```bash
gem install bundler jekyll
cd docs
jekyll serve
# open http://localhost:4000
```

## Notes

- `_config.yml` still has a placeholder `url:` value (`https://[your-username].github.io/Lost-Meadows`).
  GitHub Pages serves the site correctly regardless, but you can set this to the real URL for
  accurate SEO/sitemap output.
- The dashboard page expects the pipeline log files under `GEE/TIF_Output/Logs/` (committed to the
  repo) to populate its watershed views.
