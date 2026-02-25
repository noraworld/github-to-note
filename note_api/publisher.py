from .articles import create_article, update_article_draft
from .auth import get_note_cookies
from .images import upload_markdown_images, upload_note_eyecatch_from_url


def post_to_note(
    email,
    password,
    title,
    markdown_content,
    image_path=None,
    eyecatch_image_url=None,
):
    """noteに記事を投稿するメインフロー"""
    print("1. noteにログイン中...")
    cookies = get_note_cookies(email, password)
    if not cookies:
        print("ログインに失敗したため処理を中断します。")
        return False

    print("2. 本文中の画像をアップロード中...")
    processed_markdown, embedded_image_keys = upload_markdown_images(cookies, markdown_content)

    print("3. 記事を作成中...")
    article_id, article_key = create_article(cookies, title, processed_markdown)
    if not article_id:
        return False

    image_key = None
    if image_path:
        print("4. 画像をアップロード中...")
        # image_key, _ = upload_image(cookies, image_path)

    print("5. 記事を下書き保存中...")
    success = update_article_draft(
        cookies,
        article_id,
        article_key,
        title,
        processed_markdown,
        image_key,
        embedded_image_keys,
    )
    if not success:
        return False

    if eyecatch_image_url:
        print("6. YAML image をサムネイルとしてアップロード中...")
        upload_note_eyecatch_from_url(cookies, article_id, eyecatch_image_url)

    print("\n✅ 投稿完了！")
    print(f"記事URL: https://note.com/your_username/n/{article_key}")
    return True
