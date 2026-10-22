# Publish `devsweep` on GitHub

This guide publishes the existing local repository as a **public** GitHub repository named `devsweep`.

The commands below assume:

- You are working from the repository root.
- Your local branch is named `main`.
- The repository currently has no GitHub remote configured.
- You already have a GitHub account.

## 1. Open a terminal in the repository

From the project directory, verify that you are in the right repository:

```bash
cd /home/abhi/devsweep
git status
git branch --show-current
```

The branch should be `main`. The working tree should be clean, or contain only changes that you intend to publish.

## 2. Check for files that should not be public

Before making the repository public, inspect the files that Git will publish:

```bash
git status --short
git ls-files
```

Do **not** publish passwords, API keys, access tokens, private certificates, `.env` files, personal data, or other confidential material. Add unwanted files to `.gitignore`, then check the status again.

If a secret was already committed, removing the file in a new commit is not enough because the secret remains in Git history. Revoke or rotate the secret before publishing and clean the history separately.

## 3. Create the GitHub repository in a browser

1. Sign in to GitHub.
2. Open the **New repository** page.
3. Set **Repository name** to `devsweep`.
4. Choose **Public**.
5. Do **not** initialize it with a README, `.gitignore`, or license. This local repository already contains project files and commits.
6. Click **Create repository**.

After GitHub creates the repository, keep the new repository page open. The page will show the repository URL and setup commands.

## 4. Add GitHub as the `origin` remote

Replace `<YOUR_GITHUB_USERNAME>` with your GitHub username:

```bash
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/devsweep.git
git remote -v
```

You should see the new GitHub URL for both fetch and push.

If `origin` already exists, inspect it instead of adding it again:

```bash
git remote get-url origin
```

To correct an existing URL:

```bash
git remote set-url origin https://github.com/<YOUR_GITHUB_USERNAME>/devsweep.git
```

## 5. Commit any final local changes

If `git status` showed changes that should be included, review and commit them:

```bash
git diff
git add .
git diff --cached
git commit -m "chore: prepare repository for GitHub"
```

If there are no changes to commit, continue to the next step. Do not create an empty commit just for publishing.

## 6. Push the `main` branch

Push the local code and establish the upstream tracking branch:

```bash
git push -u origin main
```

If GitHub asks for credentials over HTTPS, use your GitHub username and a GitHub personal access token instead of your account password. GitHub no longer accepts account passwords for Git operations over HTTPS.

## 7. Confirm that the repository is public

Open the repository page in a browser:

```text
https://github.com/<YOUR_GITHUB_USERNAME>/devsweep
```

Confirm that:

- The repository visibility is **Public**.
- The expected files are present.
- The latest commit appears on the `main` branch.
- The README renders correctly.

You can also verify the local branch and remote tracking configuration:

```bash
git status
git branch -vv
git remote -v
```

## Optional: create and publish with GitHub CLI

If GitHub CLI is installed and authenticated, the browser repository-creation steps can be replaced with:

```bash
gh auth login
```

Check the result with:

```bash
gh repo view <YOUR_GITHUB_USERNAME>/devsweep --web
```

## Common problems

### `remote origin already exists`

Inspect the current remote and update it if necessary:

```bash
git remote -v
```

### `rejected because the remote contains work`

This usually means the GitHub repository was initialized with a README, license, or `.gitignore`. For a new repository, the simplest fix is to delete and recreate it without initializing any files, then run the push command again.

Do not force-push unless you have verified that overwriting the remote history is safe.

### Authentication failed

For HTTPS, use a personal access token when Git asks for a password. Alternatively, configure an SSH key and use an SSH remote:

```bash
git remote set-url origin git@github.com:<YOUR_GITHUB_USERNAME>/devsweep.git
```

### The repository should not be public yet

Create it as **Private** instead. Visibility can be changed later from the repository's **Settings → General → Danger Zone** section after reviewing the contents and history.
