import argparse
from github import Github
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import pandas as pd

def get_repo_details(repo):
    try:
        repo_name = repo.name
        repo_url = repo.html_url
        default_branch = repo.default_branch

        # Get branches
        try:
            branches = [branch.name for branch in repo.get_branches()]
            if not branches:
                branches = "EMPTY"
            else:
                branches = ', '.join(branches)
        except Exception:
            branches = "EMPTY"

        # Get last commit date
        try:
            last_commit_date = repo.get_branch(default_branch).commit.commit.author.date
        except Exception:
            last_commit_date = "EMPTY"

        # Get contributors
        try:
            contributors = repo.get_contributors()
            contributor_usernames = [contrib.login for contrib in contributors]
            contributor_emails = [contrib.email for contrib in contributors if contrib.email]

            if not contributor_usernames:
                contributor_usernames = "EMPTY"
            else:
                contributor_usernames = ', '.join(contributor_usernames)

            if not contributor_emails:
                contributor_emails = "EMPTY"
            else:
                contributor_emails = ', '.join(contributor_emails)
        except Exception:
            contributor_usernames = "EMPTY"
            contributor_emails = "EMPTY"

        # Get unique file types in the default branch
        try:
            contents = repo.get_git_tree(default_branch, recursive=True).tree
            unique_extensions = list({content.path.split('.')[-1] for content in contents if '.' in content.path})

            if not unique_extensions:
                unique_extensions = "EMPTY"
            else:
                unique_extensions = ', '.join(unique_extensions)
        except Exception:
            unique_extensions = "EMPTY"

        return {
            'Github Org Name': repo.organization.login,
            'Repository': repo_name,
            'Repository URL': repo_url,
            'Default Branch': default_branch,
            'Branches': branches,
            'Last Commit Date For Default Branch': last_commit_date,
            'Contributor Usernames': contributor_usernames,
            'Contributor Emails': contributor_emails,
            'Unique File Types Extensions In The Default Repo': unique_extensions
        }
    except Exception as e:
        return {
            'Github Org Name': "EMPTY",
            'Repository': "EMPTY",
            'Repository URL': "EMPTY",
            'Default Branch': "EMPTY",
            'Branches': "EMPTY",
            'Last Commit Date For Default Branch': "EMPTY",
            'Contributor Usernames': "EMPTY",
            'Contributor Emails': "EMPTY",
            'Unique File Types Extensions In The Default Repo': "EMPTY"
        }

def fetch_org_repos(org_name, g):
    try:
        org = g.get_organization(org_name)
        repos = org.get_repos()
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(tqdm(executor.map(get_repo_details, repos), total=repos.totalCount, desc=f"Processing {org_name}"))
        return results
    except Exception as e:
        print(f"Error fetching repos for org {org_name}: {str(e)}")
        return []

def main(org_names, pat_token, base_url):
    g = Github(base_url=base_url, login_or_token=pat_token)
    all_data = []

    for org_name in org_names:
        org_data = fetch_org_repos(org_name, g)
        all_data.extend(org_data)

    return all_data

def export_to_html(data, filename):
    df = pd.DataFrame(data)
    df.to_html(filename, index=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch GitHub repo details and export to HTML')
    parser.add_argument('--pat_token', type=str, required=True, help='GitHub Personal Access Token')
    parser.add_argument('org_names', nargs='+', type=str, help='List of GitHub organization names')
    parser.add_argument('--base_url', type=str, default='https://api.github.com', help='Base URL for GitHub API')
    parser.add_argument('--output', type=str, default='github_repo_details.html', help='Output HTML file name')
    
    args = parser.parse_args()
    
    data = main(args.org_names, args.pat_token, args.base_url)
    export_to_html(data, args.output)
    print(f"Data exported to {args.output}")
