import os
from github import Github

def load_env(file_path=".env"):
    with open(file_path, "r") as file:
        lines = file.readlines()
    return {line.split("=")[0]: line.split("=")[1].strip() for line in lines if "=" in line and not line.startswith("#")}

def upload_to_github_secrets(repo_name, token, secrets):
    g = Github(token)
    repo = g.get_repo(repo_name)
    for key, value in secrets.items():
        print(f"Uploading {key}...")
        repo.create_secret(key, value)
    print("All secrets uploaded successfully!")

if __name__ == "__main__":
    repo_name = input("Enter the GitHub repository (e.g., user/repo): ")
    github_token = os.getenv("GITHUB_TOKEN", input("Enter your GitHub Personal Access Token: "))
    secrets = load_env()
    upload_to_github_secrets(repo_name, github_token, secrets)

