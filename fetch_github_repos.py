import argparse
from github import Github
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import pandas as pd
import os

def get_repo_details(repo):
    try:
        repo_name = repo.name
        repo_url = repo.html_url
        default_branch = repo.default_branch

        try:
            branches = [branch.name for branch in repo.get_branches()]
            branches = ', '.join(branches) if branches else "EMPTY"
        except Exception:
            branches = "EMPTY"

        try:
            last_commit_date = repo.get_branch(default_branch).commit.commit.author.date
        except Exception:
            last_commit_date = "EMPTY"

        try:
            contributors = repo.get_contributors()
            contributor_usernames = [contrib.login for contrib in contributors]
            contributor_emails = [contrib.email for contrib in contributors if contrib.email]
            contributor_usernames = ', '.join(contributor_usernames) if contributor_usernames else "EMPTY"
            contributor_emails = ', '.join(contributor_emails) if contributor_emails else "EMPTY"
        except Exception:
            contributor_usernames = "EMPTY"
            contributor_emails = "EMPTY"

        try:
            contents = repo.get_git_tree(default_branch, recursive=True).tree
            unique_extensions = list({content.path.split('.')[-1] for content in contents if '.' in content.path})
            unique_extensions = ', '.join(unique_extensions) if unique_extensions else "EMPTY"
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
    except Exception:
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

def export_to_html(data, filename):
    df = pd.DataFrame(data)
    df.to_html(filename, index=False)

def main(org_args):
    for org_arg in org_args:
        try:
            org_name, pat_token, base_url = org_arg.split(",")
        except ValueError:
            print(f"Invalid format for --org argument: {org_arg}")
            print("Expected format: org_name,pat_token,base_url")
            continue

        g = Github(base_url=base_url.strip(), login_or_token=pat_token.strip())
        data = fetch_org_repos(org_name.strip(), g)
        output_file = f"{org_name.strip()}_repo_details.html"
        export_to_html(data, output_file)
        print(f"✅ Exported data for {org_name.strip()} to {output_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch GitHub repo details and export to HTML')
    parser.add_argument(
        '--org',
        action='append',
        required=True,
        help='Organization input in the format org_name,pat_token,base_url. You can specify --org multiple times.'
    )

    args = parser.parse_args()
    main(args.org)
