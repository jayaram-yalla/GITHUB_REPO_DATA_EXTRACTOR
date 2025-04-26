import argparse
import os
import pandas as pd
import time
from github import Github
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import functools

# Constants
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Rate-limit handler
def wait_for_rate_limit(github):
    try:
        core_rate_limit = github.get_rate_limit().core
        if core_rate_limit.remaining == 0:
            reset_time = core_rate_limit.reset.timestamp()
            sleep_time = reset_time - time.time()
            if sleep_time > 0:
                print(f"[!] Rate limit reached. Sleeping for {int(sleep_time)} seconds.")
                time.sleep(sleep_time + 1)
    except Exception as e:
        print(f"[!] Failed to fetch rate limit: {e}. Sleeping 60 seconds as fallback.")
        time.sleep(60)

# Retry decorator with rate-limit awareness
def retry_on_failure(retries=3, delay=5):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if hasattr(e, 'status') and e.status == 403 and 'rate limit' in str(e).lower():
                        github = kwargs.get('g')
                        if github:
                            print("[!] Rate limit hit during retry. Waiting...")
                            wait_for_rate_limit(github)
                        continue
                    print(f"[!] Retry {i + 1}/{retries} failed: {e}")
                    time.sleep(delay)
            repo = kwargs.get('repo')
            return {
                'Repository Full Name': repo.full_name if repo else "UNKNOWN",
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
        return wrapper
    return decorator

@retry_on_failure()
def get_repo_details(repo, g):
    wait_for_rate_limit(g)

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

    # Contributor usernames and emails (via commits if needed)
    try:
        contributor_usernames = []
        contributor_emails = set()

        contributors = repo.get_contributors()
        for contributor in contributors:
            contributor_usernames.append(contributor.login)

            if not contributor.email:
                try:
                    commits = repo.get_commits(author=contributor)
                    for commit in commits:
                        email = commit.commit.author.email
                        if email:
                            contributor_emails.add(email)
                            break  # Use the first email found
                except Exception:
                    continue
            else:
                contributor_emails.add(contributor.email)

        contributor_usernames = ', '.join(contributor_usernames) if contributor_usernames else "EMPTY"
        contributor_emails = ', '.join(contributor_emails) if contributor_emails else "EMPTY"

    except Exception as e:
        print(f"[!] Error fetching contributors for {repo.full_name}: {e}")
        contributor_usernames = "EMPTY"
        contributor_emails = "EMPTY"

    try:
        contents = repo.get_git_tree(default_branch, recursive=True).tree
        unique_extensions = list({content.path.split('.')[-1] for content in contents if '.' in content.path})
        unique_extensions = ', '.join(unique_extensions) if unique_extensions else "EMPTY"
    except Exception:
        unique_extensions = "EMPTY"

    return {
        'Repository Full Name': repo.full_name,
        'Github Org Name': repo.organization.login if repo.organization else "UNKNOWN",
        'Repository': repo_name,
        'Repository URL': repo_url,
        'Default Branch': default_branch,
        'Branches': branches,
        'Last Commit Date For Default Branch': last_commit_date,
        'Contributor Usernames': contributor_usernames,
        'Contributor Emails': contributor_emails,
        'Unique File Types Extensions In The Default Repo': unique_extensions
    }

def fetch_org_repos(org_name, g, cache_file):
    try:
        wait_for_rate_limit(g)
        org = g.get_organization(org_name)
        wait_for_rate_limit(g)
        repos = list(org.get_repos())

        existing_df = pd.read_csv(cache_file) if os.path.exists(cache_file) else pd.DataFrame()
        done_repos = set(existing_df['Repository Full Name']) if not existing_df.empty else set()

        final_results = existing_df.to_dict('records')

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for repo in repos:
                if repo.full_name in done_repos:
                    continue
                futures.append(executor.submit(get_repo_details, repo=repo, g=g))

            for future in tqdm(futures, desc=f"Processing {org_name}", total=len(futures)):
                result = future.result()
                final_results.append(result)
                pd.DataFrame(final_results).to_csv(cache_file, index=False)

        return final_results

    except Exception as e:
        if hasattr(e, 'status') and e.status == 403 and 'rate limit' in str(e).lower():
            print("[!] Rate limit hit while fetching org or listing repos. Waiting and retrying...")
            wait_for_rate_limit(g)
            return fetch_org_repos(org_name, g, cache_file)
        else:
            print(f"[!] Error fetching repos for org {org_name}: {str(e)}")
            return []

def export_to_html(data, filename):
    df = pd.DataFrame(data)
    df.drop(columns=['Repository Full Name'], inplace=True, errors='ignore')
    df.to_html(filename, index=True)

def main(org_args):
    for org_arg in org_args:
        try:
            org_name, pat_token, base_url = org_arg.split(",")
        except ValueError:
            print(f"[!] Invalid format for --org argument: {org_arg}")
            print("    Expected format: org_name,pat_token,base_url")
            continue

        g = Github(base_url=base_url.strip(), login_or_token=pat_token.strip())
        cache_file = os.path.join(CACHE_DIR, f"{org_name.strip()}_repo_cache.csv")

        data = fetch_org_repos(org_name.strip(), g, cache_file)
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
