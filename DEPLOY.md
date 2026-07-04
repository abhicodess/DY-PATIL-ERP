# Deployment Guide for College ERP on Render.com

This guide provides step-by-step instructions to deploy the College ERP system on Render.com tonight.

---

## Prerequisites
1. A [GitHub](https://github.com) account.
2. A [Render](https://render.com) account.
3. Git installed locally.

---

## Step 1: Push Project to GitHub

1. Initialize git (if not already done), stage files, and commit:
   ```bash
   git init
   git add .
   git commit -m "Configure deployment files for Render"
   ```
2. Create a new repository on GitHub named `college-erp`.
3. Link your local project to GitHub and push to the `main` branch:
   ```bash
   git remote add origin https://github.com/your-username/college-erp.git
   git branch -M main
   git push -u origin main
   ```

---

## Step 2: Set Up Services on Render

We will use the **Blueprint (`render.yaml`)** to deploy all services automatically.

1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. Click **New** (top right) and select **Blueprint**.
3. Connect your GitHub repository `college-erp`.
4. Render will read `render.yaml` and prompt you to create an **Environment Group** named `college-erp-env`.
5. Enter all environment variables inside the environment group (see [Environment Variables](#environment-variables)).
6. Click **Approve** to provision and deploy:
   - **PostgreSQL** (`erp-db`)
   - **Redis** (`erp-redis`)
   - **Gunicorn Web Server** (`college-erp`)
   - **Celery Worker** (`college-erp-worker`)

---

## Environment Variables

You must set these variables in the **college-erp-env** Environment Group on Render:

| Key | Description / Recommended Value |
| :--- | :--- |
| `SECRET_KEY` | Hex secret (min 32 chars). Generate with: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_SECRET_KEY` | Hex secret (min 32 chars). Generate with: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `POSTGRES_PASSWORD` | Secure password for database user (e.g. `erpDBpass2026!`) |
| `FLASK_APP` | `app:create_app()` |
| `FLASK_ENV` | `production` |
| `DEBUG` | `false` |
| `PORT` | `8000` |
| `SERVE_REACT_SPA` | `false` |
| `ADMIN_PASSWORD` | Superadmin login password (e.g. `yourSecureAdminPass123`) |
| `ADMIN_PASSWORD_HASH` | Superadmin password hash. Generate with `scripts/create_admin.py` or set matching scrypt hash. |
| `DEFAULT_STUDENT_PASSWORD` | Default password for seeded students |
| `DEFAULT_FACULTY_PASSWORD` | Default password for seeded faculty |

---

## Step 3: Run Database Initialization

Once the database and web service are running:

1. In the Render Dashboard, open the **Web Service** (`college-erp`).
2. Click on the **Shell** tab on the left sidebar.
3. Run the database setup script:
   ```bash
   python scripts/init_db.py
   ```
4. Seed test users (optional):
   ```bash
   python scripts/seed_load_users.py
   ```
5. Configure your admin credentials:
   ```bash
   export ADMIN_EMAIL=admin@dypatil.edu
   export ADMIN_PASSWORD=yourSecureAdminPass123
   python scripts/create_admin.py
   ```
   *Take the generated password hash and save it in the Render Environment Group as `ADMIN_PASSWORD_HASH`.*

---

## Step 4: Test the Deployment

1. Locate the public URL of your web service in Render (e.g., `https://college-erp.onrender.com`).
2. Open `/health` in your browser. You should receive a `200 OK` response:
   ```json
   {
     "status": "ok",
     "timestamp": "2026-06-25T13:24:03Z"
   }
   ```
3. Open the homepage, select **Admin** role, and log in:
   - **Username**: `admin`
   - **Password**: `yourSecureAdminPass123`

---

## Common Errors & Troubleshooting

### 1. `RuntimeError: SECRET_KEY is too short (must be 32+ chars)`
- **Cause**: The `SECRET_KEY` or `JWT_SECRET_KEY` variable is missing or too short.
- **Fix**: Check your Environment Group on Render and verify that both keys have been set and are at least 32 characters long.

### 2. `OperationalError: connection to server at ... failed`
- **Cause**: Web app is starting before the PostgreSQL database is fully initialized.
- **Fix**: Re-deploy the web service on Render once the database service is marked active/healthy.

### 3. Celery worker is failing to process tasks
- **Cause**: Redis connection failed or Redis URL is incorrect.
- **Fix**: Ensure `REDIS_URL` is correctly linked from the Redis service connection string.
