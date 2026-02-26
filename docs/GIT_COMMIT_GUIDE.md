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

## Version Commits

### Policy
`plan.md`의 버전 항목을 **모두 완료한 후** 버전 커밋을 생성한다.
개별 작업 중에는 논리적 단위로 커밋하되, 버전 완료 시 최종 summary 커밋을 추가한다.

### Format

버전 릴리스 완료 시:
```
release: v0.9.1

- 인라인 CSS 제거 및 components.css 도입
- 보안 취약점 수정 (Z-01, C-01)
- 문서 정리 (plan.md, ARCHITECTURE.md)
```

긴급 패치(프로덕션 버그 수정) 시:
```
hotfix: v0.9.1

- fix critical issue: 서버 시작 실패 수정
```

### GitHub Actions Release

클라이언트 EXE 빌드 및 GitHub Release 생성:

```bash
# 1. 태그 생성
git tag client-v0.8.8

# 2. 태그 푸시 (build_client.yml 트리거)
git push origin client-v0.8.8
```

Workflow:
1. `build_client.yml` 트리거
2. Windows EXE 빌드 (`WCMS-Client.exe`)
3. GitHub Release 생성
4. 서버에 새 버전 알림 (설정 시)

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

- [ ] `git status` 확인
- [ ] 테스트 실행 (`uv run python manage.py test`)
- [ ] 커밋 메시지 형식 준수
- [ ] 불필요한 파일 미포함 (`.env`, `*.db`, `flask_session/`)
- [ ] 버전 커밋 시: `plan.md` 해당 버전 항목 전부 완료 확인
