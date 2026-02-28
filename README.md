# Post to note.com GitHub Action

This repository provides a Docker-based GitHub Action that posts markdown content to note.com as a draft.

## Use from another repository

Create a workflow in the calling repository, for example `.github/workflows/post-to-note.yml`:

```yaml
name: Post to note

on:
  workflow_dispatch:
    inputs:
      content:
        description: Markdown content (with YAML front matter)
        required: true
        type: string

jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - name: Post to note
        uses: noraworld/github-to-note@main
        with:
          note_email: ${{ secrets.NOTE_EMAIL }}
          note_password: ${{ secrets.NOTE_PASSWORD }}
          content: ${{ github.event.inputs.content }}
```

## Inputs

- `note_email` (required): note.com login email
- `note_password` (required): note.com login password
- `content` (optional): markdown content string
- `content_file` (optional): path to markdown file (`title` and optional `note_id` are read from YAML front matter)
- `image_path` (optional): local image path for eyecatch upload
- `article_id` (optional): existing note article ID to update (overrides YAML `note_id`)
- `write_note_id` (optional): if truthy, writes generated `note_id` back to `content_file` on successful new post
- `publish` (optional): if truthy, publish article instead of saving draft

Note: You must provide either `content` or `content_file`, and include `title` in YAML front matter.
If either `article_id` input/option or YAML `note_id` exists, the action updates that article; if neither exists, it creates a new article.
If `write_note_id` is enabled, `note_id` is written only when a new article is created successfully.
Publish mode is enabled when either action/CLI `publish` is true or YAML front matter has `published: true`; otherwise draft mode is used.

## Example with `content_file`

If you want to pass a markdown file from the calling repository:

```yaml
name: Post to note from file

on:
  workflow_dispatch:

jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Post to note
        uses: noraworld/github-to-note@main
        with:
          note_email: ${{ secrets.NOTE_EMAIL }}
          note_password: ${{ secrets.NOTE_PASSWORD }}
          content_file: ./sample.md
          write_note_id: "true"
          # publish: "true"
          # article_id: 148375502
```

## Example: Commit `note_id` Back in Caller Workflow

When `write_note_id: "true"` is enabled, the file is modified in the runner workspace.
To persist the updated `note_id`, commit and push in the caller workflow:

```yaml
name: Post to note and commit note_id

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Post to note
        uses: noraworld/github-to-note@main
        with:
          note_email: ${{ secrets.NOTE_EMAIL }}
          note_password: ${{ secrets.NOTE_PASSWORD }}
          content_file: ./sample.md
          write_note_id: "true"

      - name: Commit updated note_id
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add ./sample.md
          git diff --cached --quiet || git commit -m "chore: write note_id"
          git push
```

## Required secrets (in the calling repository)

- `NOTE_EMAIL`
- `NOTE_PASSWORD`

## Local Development

### 1. Install dependencies

```bash
pipenv install
```

### 2. Prepare environment variables

Create `.env` in the repository root:

```env
NOTE_EMAIL=your-note-email@example.com
NOTE_PASSWORD=your-note-password
# Optional fallback session cookies (used only if login fails)
# NOTE_COOKIE can contain full cookie header string: key1=value1; key2=value2
NOTE_COOKIE=
# Or set key cookies individually:
NOTE_SESSION_V5=
XSRF_TOKEN=
# Optional helper cookie (not always present; keep empty if unavailable)
CSRF_TOKEN=
```

### 3. Run locally

Use `pipenv run` with CLI options:

```bash
pipenv run python main.py \
  --content-file ./sample.md
```

Update an existing article:

```bash
pipenv run python main.py \
  --content-file ./sample.md \
  --article-id 148375502
```

Or set `note_id` in YAML front matter and run without `--article-id`:

```yaml
---
title: "Weekly update"
note_id: 148375502
---
```

Publish by CLI option:

```bash
pipenv run python main.py \
  --content-file ./sample.md \
  --publish
```

Show the browser (disable headless) for login debugging:

```bash
pipenv run python main.py \
  --content-file ./sample.md \
  --show-browser
```

Write generated `note_id` back to the file after successful new post:

```bash
pipenv run python main.py \
  --content-file ./sample.md \
  --write-note-id
```

You can also pass markdown directly:

```bash
pipenv run python main.py --content $'---\ntitle: \"Hello\"\n---\n# Body'
```

### 4. Optional: pass content via stdin

```bash
cat ./sample.md | pipenv run python main.py
```

## CLI Options (`main.py`)

- `--note-email`: note.com login email (falls back to `NOTE_EMAIL` or `INPUT_NOTE_EMAIL`)
- `--note-password`: note.com login password (falls back to `NOTE_PASSWORD` or `INPUT_NOTE_PASSWORD`)
- `--content`: markdown content string (falls back to `INPUT_CONTENT`)
- `--content-file`: path to markdown file (falls back to `INPUT_CONTENT_FILE`)
- `--image-path`: optional local image path for eyecatch (falls back to `INPUT_IMAGE_PATH`)
- `--article-id`: existing note article ID to update (falls back to `INPUT_ARTICLE_ID`; overrides YAML `note_id`)
- `--write-note-id`: write generated `note_id` back to `--content-file` on successful new post (falls back to `INPUT_WRITE_NOTE_ID`)
- `--publish`: publish article instead of saving draft (falls back to `INPUT_PUBLISH`; YAML `published: true` also enables publish)
- `--show-browser`: launch Chrome with UI for login debugging (equivalent to `NOTE_SHOW_BROWSER=1`)

Note: You must provide content via `--content`, `--content-file`, or stdin, and include YAML front matter with `title`.

## YAML Front Matter Fields

- `title`: required article title
- `note_id`: optional existing note article ID for update mode
- `image`: optional eyecatch/thumbnail image URL
- `published`: optional boolean (`true` to publish; otherwise draft)
- `tags`: optional string array, converted to note hashtags (e.g. `["foo", "bar"]` -> `["#foo", "#bar"]`)

### Example `content_file`

```markdown
---
title: "Weekly update"
note_id: 148375502
image: "https://example.com/eyecatch.jpg"
published: true
tags: ["foo", "bar"]
---

# Weekly update

This is just a weekly note.
```

## Disclaimer (Unofficial API)

This project uses note.com unofficial/private APIs.

- API specifications may change without notice, and this action may stop working at any time.
- Use this project responsibly and within reasonable limits (for example: avoid excessive request load, avoid spam posting).
- The developer is not responsible for any direct or indirect damages caused by using this code.
- You are responsible for complying with note.com Terms of Service and related rules when operating this project.
