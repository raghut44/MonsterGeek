

import os
import re
import openai
from groq import Groq
import subprocess
import sys
from pathlib import Path

# Set OpenAI key from env
api_key = os.getenv("GROQ_API_KEY")
# openai.api_key = os.getenv("GROQ_API_KEY")
openai.base_url = "https://api.groq.com/openai/v1"

client = Groq(
    api_key=api_key,
)

# This pattern will match full conflict blocks, including their markers
CONFLICT_BLOCK_PATTERN = re.compile(
    r"(<<<<<<< .+?\n)(.*?)(=======\n)(.*?)(>>>>>>> .+?\n)", re.DOTALL
)

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print("Error:", result.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip()

def resolve_with_gpt(dev_code, rel_code):
    prompt = f"""
You are an expert developer.

Your task is to intelligently merge two versions of code — the develop and release versions — into a clean, final version.

🚫 DO NOT explain.
🚫 DO NOT include any comments, headings, or formatting.
✅ DO return ONLY the final merged code — just the raw code block.
If lines are commented in both versions, pick any one of them. Do NOT uncomment them.

DEVELOP VERSION:
{dev_code}

RELEASE VERSION:
{rel_code}

Merged Result:
"""
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are an Expert developer in resolving Git conflicts."},
            {"role": "user", "content": prompt}
        ],
        model="llama-3.3-70b-versatile",
    )
    response = chat_completion.choices[0].message.content
    print("🔀 Merged Result:\n", response)
    return response

def extract_conflicts(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return list(CONFLICT_BLOCK_PATTERN.finditer(content)), content

def resolve_conflicts_in_file(file_path):
    conflicts, content = extract_conflicts(file_path)
    if not conflicts:
        return False

    for match in reversed(conflicts):
        dev_code_raw = match.group(2)
        rel_code_raw = match.group(4)

        # Preserve spacing: Don't strip lines, pass raw content to GPT
        dev_code = dev_code_raw.rstrip('\n')
        rel_code = rel_code_raw.rstrip('\n')

        merged_code = resolve_with_gpt(dev_code, rel_code)

        # Cleanup known junk strings like 'rigin/release'
        merged_code_cleaned = re.sub(r'\brigin/release\b', '', merged_code)

        # Preserve spacing/formatting of the original block
        start, end = match.span()
        content = content[:start] + merged_code_cleaned + content[end:]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

def main():
    if not os.path.exists("../conflicts.txt"):
        print("No conflict file list found.")
        return

    with open("../conflicts.txt") as f:
        files = [line.strip() for line in f if line.strip()]

    resolved_any = False
    for fpath in files:
        print(f"🔧 Resolving conflicts in: {fpath}")
        if resolve_conflicts_in_file(fpath):
            resolved_any = True
            print(f"✅ Resolved: {fpath}")
        else:
            print(f"⚠️ No conflicts in: {fpath}")

    if resolved_any:
        run("git config user.name 'github-actions'")
        run("git config user.email 'github-actions@github.com'")
        run("git checkout -b conflict-merge-release")

        for file in files:
            run(f"git add {file}")
        restore_non_conflicted_files(files)
        run("git commit -m 'Auto-resolved conflicts using LLM'")
        run("git push origin conflict-merge-release")
    else:
        print("No conflicts were resolved.")

def restore_non_conflicted_files(conflicted_files):
    # Get all changed files in working directory
    all_changed = run("git diff --name-only --diff-filter=AM").splitlines()
    print("All changed set")
    print(all_changed)
    conflicted_set = set(conflicted_files)
    print("conflicted set")
    print(conflicted_set)
    to_restore = [f for f in all_changed if f not in conflicted_set]

    if to_restore:
        print("🧹 Restoring non-conflicted files:")
        for file in to_restore:
            print("  ➤", file)
        run("git restore " + " ".join(to_restore))
    else:
        print("✅ No non-conflicted files to restore.")
        

if __name__ == "__main__":
    main()
