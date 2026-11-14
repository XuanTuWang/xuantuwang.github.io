# Levent · Parallel portfolio

The GitHub Pages copy of [Levent's personal site](https://levent.top/showcase/), with the portfolio, resume, project atlas and Agent Systems course.

The expected public URL is **https://xuantuwang.github.io/showcase/**. The root URL opens this page. The existing `levent.top` domain stays on its current server; this repository has no custom-domain configuration.

## Build and publish

Select **GitHub Actions** in Settings → Pages. A push to `main` or a manual workflow run builds and publishes the site.

The build uses `source-manifest.json` to pin the public release and verifies each downloaded file’s SHA-256 before packaging it. The server-side editor is represented by a link to its existing server page. `content-snapshot.json` supplies the public catalog text without requiring cross-origin API access. The deployed Pages artifact contains the full static website and remains available independently of the build source.

EventOS and the content editor open their existing server-hosted pages. Other project pages and the 23-chapter Agent Systems course are served from GitHub Pages. No backend code, credentials, deployment keys or private project folders are included.

To build locally with Python 3.12 or later:

```sh
python3 scripts/build_pages.py --output _site
python3 -m http.server 8769 --directory _site
```

When publishing a newer portfolio release, refresh the pinned source manifest and public content snapshot together, then push them. The build stops if origin bytes differ from the pinned release.
