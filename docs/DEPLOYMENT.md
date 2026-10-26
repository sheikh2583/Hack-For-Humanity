# Dhoa deployment

The dashboard displays precomputed screening results. Keep
`data/processed/kilns_prioritised.parquet` available in the checkout or Space
files before launching it. `app/startup.py` checks for this file and prints
setup guidance when it is missing. It does not generate data. No GPU or Earth
Engine access is needed at dashboard runtime.

## Option 1 — Local

Prerequisites: Python 3.12, a virtual environment with `requirements.txt`
installed, and `data/processed/kilns_prioritised.parquet` already generated.
From the repository root, in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python app\startup.py
streamlit run app\streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501). The app uses the
repository's processed data. If the startup check reports the parquet is
missing, generate or copy it into the stated path and start the app again.

## Option 2 — Streamlit Community Cloud

This is the recommended public-URL option for a submission. Community Cloud
deploys a GitHub repository; it can use a public repository or one you have
connected and authorized. Follow Streamlit's current
[deployment steps](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy):

1. Push the full project source to GitHub, including `app/`, `src/`,
   `config/rules.yaml`, `.streamlit/config.toml`, and both dependency files.
   Community Cloud checks the entrypoint directory before the repository root;
   `app/requirements.txt` delegates to the CPU-only root `requirements.txt` so
   the development `uv.lock` does not replace the dashboard dependency set.
2. Make `data/processed/kilns_prioritised.parquet` available from the deployed
   checkout. The local `data/processed/` directory is git-ignored, so adding a
   local file alone will not put it in the cloud repository. Commit it with
   Git LFS if appropriate, or adapt the app to retrieve it from a separately
   hosted data source.
3. Visit [share.streamlit.io](https://share.streamlit.io), connect GitHub,
   create an app, and select the repository, branch, and main file
   `app/streamlit_app.py`.
4. Choose Python 3.12 in Advanced settings if available, deploy, and confirm
   the startup check finds the parquet in the cloud checkout.

### Inspector Portal sign-in

Staff sign-in is disabled until a credential is configured. To enable private
staff access on Community Cloud, open the app's **Settings → Secrets** and add:

```toml
staff_passcode = "replace-with-a-long-private-passcode"
```

Save the secret and reboot the app. The sign-in form then appears in the
Inspector Portal. Keep this value private and do not add it to the repository.

For a public presentation demo, set `staff_passcode` to a dummy passcode and
also add `demo_mode = true`. The portal shows a **Fill demo credentials**
button; clicking it fills the dummy passcode and Demo display name, and the
user still presses **Sign in**. Anyone visiting the public app can use this
button and gets full Inspector write access, so never use a real staff
passcode or enable this on a production portal.

The app does not generate the parquet at startup. `app/startup.py` only checks
for it and prints clear setup instructions. Community Cloud runs the app from
the repository root; keep paths and required source/config files in that
repository. Large or frequently updated parquet files can make Git history
heavy; Git LFS or external hosting may be preferable. See Streamlit's
[file organization guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization)
for repository files, configuration placement, and Git LFS details.

## Option 3 — Hugging Face Spaces

Spaces currently deprecates the built-in Streamlit SDK option. To host this
Streamlit app, create a Space using the **Docker SDK** and the official
[Streamlit Docker template](https://huggingface.co/spaces/streamlit/streamlit-template-space).
The template route and port requirements are documented in the
[Hugging Face Streamlit Spaces guide](https://huggingface.co/docs/hub/main/spaces-sdks-streamlit).

1. Create a Space at [huggingface.co/spaces](https://huggingface.co/spaces),
   select Docker, then use the Streamlit template.
2. Upload the complete runtime source, not only the entrypoint: `app/`,
   `src/`, `config/rules.yaml`, `.streamlit/config.toml`,
   `requirements.txt`, and `data/processed/kilns_prioritised.parquet`.
3. Keep or adapt the template's Dockerfile so it installs `requirements.txt`
   and launches the project entrypoint on port 8501. For example:

   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   COPY requirements.txt ./
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   EXPOSE 8501
   CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
   ```

4. In the Space `README.md` metadata, set `sdk: docker` and `app_port: 8501`.
   Let the Space rebuild, then check its build logs and public app URL.

The parquet is precomputed. Runtime needs no inference, training, GPU, or Earth
Engine export. The whole source tree and its configuration files are still
required because the dashboard imports project modules and reads
`config/rules.yaml`. Check the Space's storage and upload limits before
uploading larger data files.

## Files this app needs

- `app/streamlit_app.py` and its sibling `app/` modules
- `src/` modules imported by the app
- `config/rules.yaml`
- `data/processed/kilns_prioritised.parquet`
- `requirements.txt` and `.streamlit/config.toml`

`requirements.txt` includes the requested dashboard packages plus `pyproj`,
`numpy`, and `rich`, which are directly used by the imported project modules.
