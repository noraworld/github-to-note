# Post to note.com GitHub Action

This repository provides a Docker-based GitHub Action that posts markdown content to note.com as a draft.

## Use from another repository

Create a workflow in the calling repository, for example `.github/workflows/post-to-note.yml`:

```yaml
name: Post to note

on:
  workflow_dispatch:
    inputs:
      title:
        description: Article title
        required: true
        type: string
      content:
        description: Markdown content
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
          title: ${{ github.event.inputs.title }}
          content: ${{ github.event.inputs.content }}
```

## Inputs

- `note_email` (required): note.com login email
- `note_password` (required): note.com login password
- `title` (required): article title
- `content` (optional): markdown content string
- `content_file` (optional): path to markdown file
- `image_path` (optional): local image path for eyecatch upload

Note: You must provide either `content` or `content_file`.

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
          title: Weekly Update
          content_file: ./content/weekly-update.md
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
```

### 3. Run locally

Use `pipenv run` with CLI options:

```bash
pipenv run python main.py \
  --title "My Article Title" \
  --content-file ./content/weekly-update.md
```

You can also pass markdown directly:

```bash
pipenv run python main.py \
  --title "My Article Title" \
  --content "# Hello from local run"
```

### 4. Optional: pass content via stdin

```bash
cat ./content/weekly-update.md | pipenv run python main.py --title "From stdin"
```

## CLI Options (`main.py`)

- `--note-email`: note.com login email (falls back to `NOTE_EMAIL` or `INPUT_NOTE_EMAIL`)
- `--note-password`: note.com login password (falls back to `NOTE_PASSWORD` or `INPUT_NOTE_PASSWORD`)
- `--title`: article title (falls back to `NOTE_TITLE` or `INPUT_TITLE`)
- `--content`: markdown content string (falls back to `INPUT_CONTENT`)
- `--content-file`: path to markdown file (falls back to `INPUT_CONTENT_FILE`)
- `--image-path`: optional local image path for eyecatch (falls back to `INPUT_IMAGE_PATH`)

Note: You must provide content via `--content`, `--content-file`, or stdin.
