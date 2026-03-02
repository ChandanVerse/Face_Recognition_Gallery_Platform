# ⚠️ Security Notice

## Credentials Exposed in Git History

**Your MongoDB and Pinecone API credentials were previously committed to git history.** Even though `.env` files are now removed from tracking, the credentials remain in your git history and are visible to anyone with access to the repository.

### What Was Exposed

- MongoDB Atlas connection string with credentials
- Pinecone API key
- JWT secret keys
- Domain/CORS configuration

### Actions You MUST Take

#### 1. **Rotate All Credentials** (CRITICAL)
Since these credentials were exposed in git, assume they are compromised:

- [ ] **MongoDB Atlas**: Change your aiGalleryUser password immediately
  - Go to: MongoDB Atlas → Database → Users → Edit → Change Password

- [ ] **Pinecone**: Regenerate your API key
  - Go to: Pinecone console → API Keys → Create new key or delete the old one

- [ ] **JWT Secret**: Update JWT_SECRET_KEY in production environment

#### 2. **Remove From Git History** (Recommended)
To completely remove sensitive data from git history, use one of these tools:

**Option A: Using `git filter-repo` (Recommended)**
```bash
# Install git-filter-repo
pip install git-filter-repo

# Remove .env files from entire history
git filter-repo --path .env --invert-paths
git filter-repo --path frontend/.env --invert-paths
```

**Option B: Using `git filter-branch` (Legacy)**
```bash
git filter-branch --tree-filter 'rm -f .env frontend/.env' HEAD
git reflog expire --expire=now --all && git gc --prune=now --aggressive
```

**⚠️ WARNING**: Both methods rewrite git history. Only do this if you control the repository and no one has cloned it or based work on recent commits.

#### 3. **If Repository is Public**
If anyone has cloned this repository while credentials were exposed:
1. Complete credential rotation immediately
2. Notify any team members
3. Force-push the cleaned history: `git push origin --force-all`

### Setup Instructions for Team Members

1. Clone the repository
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Update `.env` with actual credentials (obtained from secure team channels)
4. **NEVER commit `.env` or share it publicly**

### Preventing Future Issues

- ✅ Updated `.gitignore` now prevents `.env` files from being committed
- ✅ Use `.env.example` as a template for required variables
- ✅ Enable `git-secrets` to prevent credential commits:
  ```bash
  pip install git-secrets
  git secrets --install
  git secrets --register-aws  # for AWS credentials, adjust for your services
  ```

### Additional Resources

- [git-secrets on GitHub](https://github.com/awslabs/git-secrets)
- [git-filter-repo documentation](https://github.com/newren/git-filter-repo)
- [OWASP: Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

**Last Updated**: 2026-03-02
**Status**: Ready for GitHub push after credential rotation
