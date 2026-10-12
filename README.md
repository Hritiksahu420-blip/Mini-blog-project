# MiniBlog — Flask + SQLite

A beginner-friendly mini blog app with registration, login, posts, comments, and administrator post deletion.

## Features
- Register and log in with password hashing
- Create and read blog posts
- Add comments to posts (login required)
- Administrator can delete any post; deleting a post also deletes its comments
- SQLite database created automatically on first run
- Responsive layout

## Requirements
- Python 3.10 or newer
- pip

## Run locally

### 1. Open a terminal in this project folder
Create and activate a virtual environment (recommended).

**Windows**
```bash
python -m venv .venv
.venv\\Scripts\\activate
```

**macOS/Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install packages
```bash
pip install -r requirements.txt
```

### 3. Start the app
```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Local demo admin account
- Username: `admin`
- Password: `Admin123!`

Change these credentials for any real deployment. The default account is only for local demonstration. To choose different initial admin credentials, set `BLOG_ADMIN_USERNAME` and `BLOG_ADMIN_PASSWORD` environment variables before the first run. If the default admin already exists in `blog.db`, changing the variables will not change that existing account.

## Important security notes
- Set a strong random `SECRET_KEY` in the environment before deployment.
- The built-in Flask development server is for local development only.
- Add CSRF protection and rate limiting before deploying publicly.
- Never commit `blog.db`, passwords, or `.env` files to GitHub.

## Main routes
- `/` — list posts
- `/register` — create an account
- `/login` — log in
- `/post/new` — create a post (login required)
- `/post/<id>` — view a post and add comments
- `/admin/post/<id>/delete` — delete a post (admin only, POST request)
