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
        uses: YOUR_ORG_OR_USER/note-api-sample@main
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
        uses: YOUR_ORG_OR_USER/note-api-sample@main
        with:
          note_email: ${{ secrets.NOTE_EMAIL }}
          note_password: ${{ secrets.NOTE_PASSWORD }}
          title: Weekly Update
          content_file: ./content/weekly-update.md
```

## Required secrets (in the calling repository)

- `NOTE_EMAIL`
- `NOTE_PASSWORD`
