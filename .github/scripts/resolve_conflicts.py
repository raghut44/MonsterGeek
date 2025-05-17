import os
import re
import openai

# Set OpenAI key from env
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()

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
