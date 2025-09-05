#!/usr/bin/env python3
import os
import sys
import json
from github import Github
from swe_agent import Agent

def get_issue_details():
    """Get issue details from GitHub event"""
    token = os.environ['GITHUB_TOKEN']
    event_path = os.environ['GITHUB_EVENT_PATH']

    with open(event_path, 'r') as f:
        event_data = json.load(f)

    issue_number = event_data['issue']['number']
    repo_name = event_data['repository']['full_name']

    g = Github(token)
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(number=issue_number)

    return issue, repo

def analyze_and_fix_issue(issue, repo):
    """Analyze issue and create PR with fix"""
    # Initialize agent
    agent = Agent()

    # Parse issue body to get test details
    lines = issue.body.split('\n')
    test_info = {}
    for line in lines:
        line = line.strip()
        if line.startswith('Test:'):
            test_info['test'] = line.split('Test:')[1].strip()
        elif line.startswith('Class:'):
            test_info['class'] = line.split('Class:')[1].strip()
        elif line.startswith('Vector DB:'):
            test_info['vector_db'] = line.split('Vector DB:')[1].strip()
        elif line.startswith('Error:'):
            test_info['error'] = line.split('Error:')[1].strip()

    # Get the test file path
    class_parts = test_info['class'].split('.')
    test_file = f"backend/tests/{'/'.join(class_parts[2:])}.py"

    # Read current test file content
    try:
        with open(test_file, 'r') as f:
            current_content = f.read()
    except FileNotFoundError:
        issue.create_comment(f"Could not find test file: {test_file}")
        return

    # Generate fix using agent
    prompt = f"""
    Test failure details:
    - Test name: {test_info['test']}
    - Vector DB: {test_info['vector_db']}
    - Error: {test_info['error']}

    Current test code:
    {current_content}

    Please analyze the failure and suggest a fix.
    """

    try:
        analysis = agent.analyze(prompt)
        fix_suggestion = agent.generate_fix(current_content, analysis)

        # Create a new branch
        base_branch = repo.default_branch
        new_branch = f"fix/test-{issue.number}"
        base_ref = repo.get_git_ref(f"heads/{base_branch}")
        repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base_ref.object.sha)

        # Create/update file in the new branch
        repo.update_file(
            path=test_file,
            message=f"fix: Automated test fix for issue #{issue.number}",
            content=fix_suggestion,
            sha=repo.get_contents(test_file, ref=new_branch).sha,
            branch=new_branch
        )

        # Create pull request
        pr = repo.create_pull(
            title=f"fix: Automated test fix for {test_info['test']}",
            body=f"""
            This PR contains an automated fix for test failure in issue #{issue.number}.

            Original error:
            ```
            {test_info['error']}
            ```

            Fix analysis:
            {analysis}

            Please review the changes carefully before merging.
            """,
            head=new_branch,
            base=base_branch
        )

        # Add labels to PR
        pr.add_to_labels("automated-fix", test_info['vector_db'])

        # Comment on the issue
        issue.create_comment(f"Created PR #{pr.number} with an automated fix. Please review.")

    except Exception as e:
        issue.create_comment(f"Error while trying to create automated fix: {str(e)}")
        raise

def main():
    try:
        issue, repo = get_issue_details()
        analyze_and_fix_issue(issue, repo)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
