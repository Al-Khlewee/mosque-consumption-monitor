# Deployment Guide for Mosque Consumption Monitor

The easiest way to deploy your Streamlit application for free is using **Streamlit Community Cloud**.

## Prerequisites
1.  A **GitHub** account.
2.  The project files must be uploaded to a GitHub repository.

## Step 1: Prepare the Repository
1.  **Create a new repository** on GitHub (e.g., `mosque-monitor`).
2.  **Upload your files** to this repository.
    *   Ensure `app.py`, `utils.py`, `models.py`, and `requirements.txt` are included.
    *   *Note: The database files (`*.db`) will be ignored by default. This is fine because the app is now configured to automatically regenerate the database if it's missing!*

## Step 2: Deploy to Streamlit Cloud
1.  Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
2.  Click **"New app"**.
3.  Select your repository (`mosque-monitor`) and branch (`main`).
4.  **Main file path**: Enter `app.py`.
5.  Click **"Deploy!"**.

## Step 3: Verify
*   Wait a few minutes. Streamlit will install the dependencies from `requirements.txt`.
*   The app should launch automatically.
*   **Login**: Use the default credentials:
    *   Admin: `admin` / `admin123`
    *   Manager: `manager` / `manager123`

## Important Notes on Data Persistence
Streamlit Cloud's filesystem is **ephemeral**. This means:
*   Every time the app reboots (or you push new code), **the SQLite database will handle a reset**.
*   The `init_db()` function we added will re-seed the data, but **any new readings you entered manually via the UI will be lost** upon reboot.
*   **For permanent data storage**: You would need to connect the app to a cloud database (like Google Sheets, Supabase, or AWS RDS) instead of using a local SQLite file.
