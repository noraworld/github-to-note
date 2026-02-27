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
- `content_file` (optional): path to markdown file
- `image_path` (optional): local image path for eyecatch upload
- `article_id` (optional): existing note article ID to update (if omitted, creates a new article)

Note: You must provide either `content` or `content_file`, and include `title` in YAML front matter.

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
          # article_id: 148375502
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

Show the browser (disable headless) for login debugging:

```bash
pipenv run python main.py \
  --content-file ./sample.md \
  --show-browser
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
- `--article-id`: existing note article ID to update (falls back to `INPUT_ARTICLE_ID`)
- `--show-browser`: launch Chrome with UI for login debugging (equivalent to `NOTE_SHOW_BROWSER=1`)

Note: You must provide content via `--content`, `--content-file`, or stdin, and include YAML front matter with `title`.
