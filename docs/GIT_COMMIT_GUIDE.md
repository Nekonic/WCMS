# Git Commit Guide

This guide defines the commit rules for the WCMS project.
We follow the **Conventional Commits** specification.

---

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 1. Header (Required)

The header consists of `type`, `scope`, and `subject`.

#### Type
Must be one of the following:

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to the build process or auxiliary tools and libraries such as documentation generation
- **ci**: Changes to our CI configuration files and scripts (e.g., GitHub Actions)

#### Scope (Optional but Recommended)
Indicates the module or area affected.
- `client`
- `server`
- `api`
- `ui`
- `docs`
- `db`

#### Subject
- Use **English**.
- Use the imperative, present tense: "change" not "changed" or "changes".
- Don't capitalize the first letter.
- No dot (.) at the end.
- Keep it concise (under 50 characters if possible).

### 2. Body (Optional)
- Use **Korean** or **English** (Korean preferred for detailed explanation).
- Use the imperative, present tense.
- Explain **what** and **why** vs. how.
- Use a hyphen (-) for bullet points.

### 3. Footer (Optional)
- Reference issues or pull requests.
- Example: `Ref: #123`, `Closes: #456`

---

## Examples

### Feature
```
feat(client): add auto-update mechanism

- Implement version check on startup
- Download and execute install.cmd if update available
- Handle service restart gracefully

Ref: #42
```

### Bug Fix
```
fix(server): resolve token deletion error

- Fix issue where token string was passed instead of ID
- Update deleteToken function in registration_tokens.html
```

### Documentation
```
docs: update API documentation for v0.8.7

- Add uninstall command endpoint
- Remove keyboard parameter from create_account
```

### Refactoring
```
refactor(server): remove unused account manager route

- Delete /account/manager route from app.py
- Remove link from base.html sidebar
- Consolidate account management into index.html modal
```

---

## Workflow

1. **Check Status**
   ```bash
   git status
   ```

2. **Stage Changes**
   ```bash
   git add .
   # or specific files
   git add client/main.py
   ```

3. **Commit**
   ```bash
   git commit -m "feat(client): add auto-update mechanism" -m "- Implement version check..."
   ```

4. **Push**
   ```bash
   git push origin main
   ```

---

## Release & GitHub Actions

To trigger a release build via GitHub Actions, create and push a tag starting with `client-v`.

```bash
# 1. Create a tag
git tag client-v0.8.8

# 2. Push the tag
git push origin client-v0.8.8
```

This will:
1. Trigger the `build_client.yml` workflow.
2. Build the Windows executable (`WCMS-Client.exe`).
3. Create a GitHub Release.
4. Notify the server about the new version (if configured).

---

## .gitignore Checklist

Ensure these files are **NOT** committed:

- `__pycache__/`
- `*.pyc`
- `venv/`, `.venv/`
- `*.sqlite3`, `*.db` (except template DBs)
- `*.log`, `logs/`
- `.env`
- `.idea/`, `.vscode/`
- `dist/`, `build/`
- `*.spec`

---

## Pre-Commit Checklist

- [ ] Did you check `git status`?
- [ ] Did you run tests (`python manage.py test`)?
- [ ] Does the commit message follow the format?
- [ ] Are there any unnecessary files included?
