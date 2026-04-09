# 🚀 Push to GitHub — 3 Commands

This repo is fully ready. Follow these steps exactly.

---

## Step 1: Create the GitHub repository (browser)

Go to → https://github.com/new

- **Repository name:** `agam-automation-hub`
- **Visibility:** Private (recommended) or Public
- **⚠️ DO NOT** check "Add README", "Add .gitignore", or "Choose a license"
- Click **Create repository**

---

## Step 2: Push from your local machine (terminal)

Navigate to where you extracted/downloaded this folder, then:

```bash
cd agam-automation-hub

git init
git add .
git commit -m "Initial commit: Phase 1 complete — job search automation hub"
git branch -M main
git remote add origin https://github.com/agamsaraswat/agam-automation-hub.git
git push -u origin main
```

That's it. All 128 files will be pushed in one go.

---

## Step 3: Enable branch protection (browser)

In your new repo → **Settings → Branches → Add branch protection rule**

- **Branch name pattern:** `main`
- ✅ Check: **Require a pull request before merging**
- ✅ Check: **Require approvals** (set to 1)
- Click **Create**

---

## Step 4: Add Soumyabrata as collaborator (browser)

**Settings → Collaborators → Add people**

- Search: `soumyabrata` (his GitHub username)
- Role: **Maintain** (can push branches, can't merge to main)

---

## First Run (after push)

```bash
# One-time setup
bash scripts/setup.sh        # or: make setup

# Add your API key
nano .env                    # set ANTHROPIC_API_KEY=sk-ant-...

# Run!
make web                     # starts backend + React dashboard
# OR
make run                     # CLI job discovery only
```

Dashboard: http://localhost:8000
Frontend:  http://localhost:5173

---

## Troubleshooting

**Wrong remote URL?**
```bash
git remote set-url origin https://github.com/agamsaraswat/agam-automation-hub.git
```

**Authentication error?**
Use a GitHub Personal Access Token (not your password):
Settings → Developer settings → Personal access tokens → Generate new token (classic)
Scopes needed: `repo`

**Push rejected (non-fast-forward)?**
You accidentally initialized GitHub with a README. Fix:
```bash
git pull origin main --allow-unrelated-histories
git push origin main
```
