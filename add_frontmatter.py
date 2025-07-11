from pathlib import Path

FRONTMATTER_TEMPLATE = '''---
name: "{name}"
description: "{description}"
arguments: []
keywords:
  - placeholder
---\n\n'''

def has_yaml_frontmatter(path):
    with open(path, 'r') as f:
        first = f.readline()
        return first.strip() == "---"

def infer_name_and_description(md_path):
    # Use filename as name, first heading as description
    name = Path(md_path).stem.replace('_', ' ').replace('-', ' ').title()
    desc = ""
    with open(md_path, 'r') as f:
        for line in f:
            if line.strip().startswith("#"):
                desc = line.strip().lstrip("#").strip()
                break
    return name, desc or "No description"

def prepend_frontmatter(md_path):
    name, desc = infer_name_and_description(md_path)
    with open(md_path, 'r') as f:
        content = f.read()
    with open(md_path, 'w') as f:
        f.write(FRONTMATTER_TEMPLATE.format(name=name, description=desc) + content)

root = Path("agent_capabilities")
for md_file in root.rglob("*.md"):
    if not has_yaml_frontmatter(md_file):
        prepend_frontmatter(md_file)
        print(f"Added YAML frontmatter to {md_file}")
    else:
        print(f"Skipped {md_file} (already has frontmatter)")
