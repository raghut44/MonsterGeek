import os
import re
import openai
from groq import Groq

# Set OpenAI key from env
api_key = os.getenv("OPENAI_API_KEY")
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

def resolve_with_gpt(dev_code, rel_code):
    prompt = f"""
You are an expert developer. Resolve this git conflict by intelligently merging the two versions. Retain meaningful code from both sides.

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

    if not resolved_any:
        print("No conflicts were resolved.")

if __name__ == "__main__":
    main()
