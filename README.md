
# GitHub Repo Data Extractor (Enterprise-Ready, Resumable, Rate-Limit Safe)

This script extracts key metadata for repositories in a GitHub organization and exports it to an HTML file.

## ✅ Features
- Handles GitHub API rate limits (waits & retries safely)
- Extracts **Contributor Usernames** and **Contributor Emails** (commit-based retrieval)
- Supports large organizations via **resumable scans**
- Saves intermediate progress in `cache/`
- Exports final results to `.html` with index
- Works with both GitHub SaaS Enterprise tenants and Public GitHub

## 📦 Requirements
- Python >= 3.9
- GitHub Personal Access Token (PAT) with necessary read access

## 🛠 Installation
```bash
pip install PyGithub pandas tqdm
```

## 🚀 Usage
```bash
python fetch_github_repos_resumable.py --org "org_name,pat_token,base_url"
```

### Example
```bash
python fetch_github_repos_resumable.py --org "GITHUB_ORG_NAME,ghp_exampletoken,https://api.github.com"
```

- You can specify multiple `--org` options.
- Output HTML and cache files are generated for each organization.

## 📂 Output Files
- `cache/orgname_repo_cache.csv` — Intermediate cached results for resumability
- `orgname_repo_details.html` — Final HTML report including contributor details

## 🔗 Connect With Me
[![linkedin](https://img.shields.io/badge/linkedin-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://in.linkedin.com/in/jayaramyalla)
