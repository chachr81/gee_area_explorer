# Docker Deployment Guide (GEE Area Explorer)

[🇪🇸 Ver en Español](README.md)

This document provides the technical procedure for deploying the tool as a self-contained Docker container. This is the recommended usage method, as it guarantees a stable environment with all geospatial dependencies (GDAL, earthengine-api) pre-installed.

---

## 1. Prerequisites

Before you begin, ensure you have the following:

1.  **Docker Engine & Docker Compose**: Installed and running on your host machine.
2.  **Google Account**: An account with access enabled for [Google Earth Engine](https://signup.earthengine.google.com/).
3.  **Google Cloud Platform (GCP) Project**: An active project where queries will be billed (or use the free tier).

### GCP Project Setup (Critical Step)

For the tool to work, you must have a valid "Project ID".

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project or select an existing one.
3.  **Enable API**: In the "APIs & Services" > "Library" menu, search for **"Earth Engine API"** and enable it.
4.  **Register Project**: Go to the [GEE Code Editor](https://code.earthengine.google.com/), click your user icon (top right), and ensure your Cloud project is registered for Earth Engine use.
5.  **Get ID**: Copy the **Project ID** (e.g., `my-geo-project-12345`).

---

## 2. Environment Preparation

### Directory Structure

Create a project folder with the following structure:

```text
my-deployment/
├── docker-compose.yml      # (Provided in the repository)
├── .env                    # Environment variables file
├── data/
│   └── geojson/            # Input folder for your .geojson files
├── output/                 # Output folder for CSV results
└── logs/                   # (Optional) Execution logs
```

### Credential Configuration (.env)

Create a `.env` file in the root with the following content:

```ini
GEE_PROJECT=your-project-id-here
```

---

## 3. Build and Installation

Build the Docker image (this only needs to be done once):

```bash
docker-compose build cli
```

---

## 4. Authentication (One-Time Step)

Authorize the container to access Google Earth Engine. This step saves a persistent token.

```bash
docker-compose run --rm cli earthengine authenticate
```

**Procedure:**
1.  Open the URL that appears in the terminal.
2.  Authorize access with your Google account.
3.  Copy the authorization code and paste it into the terminal.

---

## 5. Running the Tool

### Interactive Mode (Recommended for Exploration)
Launches a visual menu that guides you through the process.

```bash
docker-compose run --rm cli
```

### Command Line Mode (For Scripts)
Ideal for integration into automated workflows.

```bash
docker-compose run --rm cli python scripts/gee_search.py data/geojson/your_area.geojson
```

---

## 6. Common Troubleshooting

*   **Error: "Project ID not found"**: Verify that the `.env` file exists and contains the `GEE_PROJECT` variable.
*   **Error: "Credential path not found"**: Repeat the authentication step.
*   **Permissions on Linux**: If files in `output/` are created by `root`, change their ownership with `sudo chown -R $USER:$USER output/`.