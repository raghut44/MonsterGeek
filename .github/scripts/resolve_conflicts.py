import os
import re
import openai
from groq import Groq
import subprocess
import sys
from pathlib import Path

# Set OpenAI key from env
api_key = "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"
#openai.api_key = os.getenv("GROQ_API_KEY")
openai.base_url = "https://api.groq.com/openai/v1"
MODEL = "mixtral-8x7b-32768"

client = Groq(
    # This is the default and can be omitted
    api_key=api_key,
)

CONFLICT_PATTERN = re.compile(
    r"<<<<<<< .+?\n(.*?)=======\n(.*?)>>>>>>> .+?", re.DOTALL
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
If lines are commented in both version pick any one of it.

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
    print("result === "+chat_completion.choices[0].message.content)
    return chat_completion.choices[0].message.content

def extract_conflicts(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return list(CONFLICT_PATTERN.finditer(content)), content

def resolve_conflicts_in_file(file_path):
    conflicts, content = extract_conflicts(file_path)
    if not conflicts:
        return False

    for match in reversed(conflicts):
        dev_code = match.group(1).strip()
        print("devcode "+dev_code)
        rel_code = match.group(2).strip()
        print("relcode "+rel_code)
        merged_code = resolve_with_gpt(dev_code, rel_code)
        start, end = match.span()
        content = content[:start] + merged_code + content[end:]

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
    run("git config user.name 'github-actions'")
    run("git config user.email 'github-actions@github.com'")
    run(f"git checkout -b conflict-merge-release")

    for file in files:
        run(f"git add {file}")
    run(f"git commit -m 'Auto-resolved conflicts using LLM'")
    run(f"git push origin conflict-merge-release")
    if not resolved_any:
        print("No conflicts were resolved.")

if __name__ == "__main__":
    main()
