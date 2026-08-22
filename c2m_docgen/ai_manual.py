"""Sends a screenshot to Claude's API and asks it to write a detailed,
plain-language user-manual explanation of every piece of functionality
visible in the image -- charts, buttons, filters, table columns,
navigation, all of it.

This is independent of the scan itself: you point it at any .png already
sitting in the output folder (from a past or current scan run) and get
back a manual section for that specific screenshot, saved as a sibling
.md file next to the image.

Requires:
    pip install anthropic
    export ANTHROPIC_API_KEY="sk-ant-..."
"""
import base64
import os

import anthropic

DEFAULT_MODEL = "claude-sonnet-5"

MANUAL_PROMPT = """You are a technical writer producing a user manual page for internal staff who are unfamiliar with this dashboard.

Look at the attached screenshot and write a manual section that:
1. States what page/view this is and its overall purpose, in one or two sentences.
2. Walks through EVERY distinct piece of UI visible -- charts (name each one and what it shows), buttons (what each one does), dropdown filters, date filters, table columns, tabs/navigation, and any other interactive element. Don't skip anything visible, even small icons or controls.
3. For each element, explain what it's for and what a user would do with it -- not just that it exists.
4. Uses clear markdown headers and bullet points. Do not use raw HTML.
5. Does not invent functionality that isn't visibly present in the screenshot -- if something is ambiguous, describe what's visible rather than guessing at backend behavior.

Write only the manual section itself, starting with a "##" markdown header naming the page. No preamble like "Here is the manual"."""


def _encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def list_screenshots(output_dir):
    """Walks output_dir for every .png, returning (display_label, full_path)
    pairs sorted by path so product subfolders group together."""
    results = []
    for root, _dirs, files in os.walk(output_dir):
        for name in sorted(files):
            if name.lower().endswith(".png"):
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, output_dir)
                results.append((rel_path, full_path))
    return sorted(results, key=lambda pair: pair[0])


def pick_screenshot_interactively(output_dir):
    """Simple numbered CLI picker over every screenshot found under
    output_dir. Returns the chosen file path, or None if the user
    cancels/there's nothing to pick from."""
    screenshots = list_screenshots(output_dir)
    if not screenshots:
        print(f"No .png files found under '{output_dir}'.")
        return None

    print(f"\nFound {len(screenshots)} screenshot(s):\n")
    for i, (label, _path) in enumerate(screenshots, start=1):
        print(f"  [{i}] {label}")

    choice = input("\nPick a screenshot number (or 'q' to cancel): ").strip()
    if choice.lower() == "q":
        return None
    try:
        idx = int(choice)
        if not (1 <= idx <= len(screenshots)):
            raise ValueError
    except ValueError:
        print("Invalid selection.")
        return None

    return screenshots[idx - 1][1]


def generate_manual_for_screenshot(image_path, api_key=None, model=DEFAULT_MODEL):
    """Sends image_path to Claude's vision API and returns the manual
    section text (markdown). Raises if the API call fails -- caller
    decides how to surface that."""
    client = anthropic.Anthropic(api_key=api_key)  # falls back to ANTHROPIC_API_KEY env var

    image_b64 = _encode_image(image_path)
    media_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                    },
                    {"type": "text", "text": MANUAL_PROMPT},
                ],
            }
        ],
    )

    return "".join(block.text for block in response.content if block.type == "text")


def save_manual_text(image_path, manual_text):
    """Writes the generated manual text to a sibling .md file next to the
    screenshot (e.g. 2026-08-15_tech-stack.png -> 2026-08-15_tech-stack.ai-manual.md)."""
    base, _ext = os.path.splitext(image_path)
    out_path = f"{base}.ai-manual.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(manual_text)
    return out_path


def main(output_dir="screenshots", image_path=None, api_key=None, model=DEFAULT_MODEL):
    """If image_path is given, uses it directly (skips the picker) --
    handy for scripting/automation. Otherwise prompts interactively."""
    chosen = image_path or pick_screenshot_interactively(output_dir)
    if not chosen:
        print("No screenshot selected. Exiting.")
        return

    if not os.path.isfile(chosen):
        print(f"File not found: {chosen}")
        return

    print(f"\nSending {chosen} to Claude ({model})...")
    try:
        manual_text = generate_manual_for_screenshot(chosen, api_key=api_key, model=model)
    except Exception as e:
        print(f"API call failed: {e}")
        return

    out_path = save_manual_text(chosen, manual_text)
    print(f"\nSaved manual to: {out_path}\n")
    print(manual_text)


if __name__ == "__main__":
    main()
