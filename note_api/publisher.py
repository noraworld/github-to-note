from .articles import (
    create_article,
    publish_article,
    update_article_draft,
    update_existing_article,
)
from .auth import get_note_cookies
from .images import upload_markdown_images, upload_note_eyecatch_from_url
from .markdown import sanitize_markdown


def post_to_note(
    email,
    password,
    title,
    markdown_content,
    image_path=None,
    eyecatch_image_url=None,
    article_id=None,
    publish=False,
    hashtags=None,
):
    """noteに記事を投稿するメインフロー"""
    markdown_content = sanitize_markdown(markdown_content)

    print("1. noteにログイン中...")
    cookies = get_note_cookies(email, password)
    if not cookies:
        print("ログインに失敗したため処理を中断します。")
        return False, None, False

    print("2. 本文中の画像をアップロード中...")
    processed_markdown, embedded_image_keys = upload_markdown_images(cookies, markdown_content)

    created_new = False
    if article_id:
        print(f"3. 既存記事を更新中... (ID: {article_id})")
        article_id, article_key, _ = update_existing_article(
            cookies, article_id, title, processed_markdown
        )
    else:
        print("3. 記事を作成中...")
        article_id, article_key = create_article(cookies, title, processed_markdown)
        created_new = True
    if not article_id:
        return False, None, False

    image_key = None
    eyecatch_upload = None
    if image_path:
        print("4. 画像をアップロード中...")
        # image_key, _ = upload_image(cookies, image_path)
    if eyecatch_image_url:
        print("4. YAML image をサムネイルとしてアップロード中...")
        eyecatch_upload = upload_note_eyecatch_from_url(cookies, article_id, eyecatch_image_url)
    eyecatch_image_key = eyecatch_upload.get("key") if eyecatch_upload else None

    print("5. 記事を下書き保存中...")
    success = update_article_draft(
        cookies,
        article_id,
        article_key,
        title,
        processed_markdown,
        image_key,
        embedded_image_keys,
        eyecatch_image_key=eyecatch_image_key,
    )
    if not success:
        return False, None, created_new

    if publish:
        print("6. 記事を公開中...")
        success = publish_article(
            cookies,
            article_id,
            title,
            processed_markdown,
            hashtags=hashtags,
            article_key=article_key,
            embedded_image_keys=embedded_image_keys,
            eyecatch_image_key=eyecatch_image_key,
        )
        if not success:
            return False, None, created_new

    if publish:
        print("\n✅ 公開完了！")
    else:
        print("\n✅ 投稿完了！")
    if article_key:
        print(f"記事URL: https://note.com/your_username/n/{article_key}")
    return True, str(article_id), created_new
