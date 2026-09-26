# Arctic Survival

Blender assets and an interactive Three.js field explorer. The website displays
the exported terrain and animated wildlife directly in the browser.

## Deploy to Vercel

1. Commit and push the website configuration and source files to GitHub.
2. Import `matteau94/Arctic-Survival` as a Vercel project.
3. Keep **Root Directory** at the repository root and **Framework Preset** at
   **Other**. `vercel.json` sets the build command to `npm run build` and the
   output directory to `dist`.
4. In **Settings > Git**, enable **Git Large File Storage (LFS)**, then redeploy.
   The model files are stored in LFS; without this setting the build deliberately
   fails with instructions instead of publishing broken models. Ensure the LFS
   objects have also been pushed to GitHub.
5. Open the deployment URL. The explorer is served at `/`; its existing
   `/viewer/` and model URLs also work.

Vercel serves the generated static files; no running Node server or Blender
installation is needed in production. Only browser code, vendor modules,
exported terrain, and models referenced by `viewer/data/world.json` are published.
Blender sources, scripts, logs, and review files are excluded from the website.

Official LFS setup: https://vercel.com/docs/project-configuration/git-settings

## Local development

Install Node.js (a current LTS release) and Git LFS, then run:

```sh
git lfs pull
npm start
```

Open http://127.0.0.1:8765. Run `npm run build` to validate the assets and generate
the same `dist` directory used by Vercel. No npm dependencies are required.

Models are large, so the first visit may load slowly and consume substantial
bandwidth. This deployment publishes the existing explorer, including its
scripted wildlife behavior. See [viewer/README.md](viewer/README.md) for controls
and instructions for re-exporting the scene from Blender.
