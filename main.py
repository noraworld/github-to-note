import os

from dotenv import load_dotenv

from note_api import post_to_note


load_dotenv()

EMAIL = os.getenv("NOTE_EMAIL")
PASSWORD = os.getenv("NOTE_PASSWORD")


if __name__ == "__main__":
    TITLE = "朝のコーヒーを少しだけ変えてみた 2"
    CONTENT = """
# 朝のコーヒーを少し変えてみた話

最近、朝のコーヒーの淹れ方を少しだけ変えてみました。
といっても、豆を変えたわけでも、高級な器具を買ったわけでもありません。

## 単純に、お湯の温度を少し下げてみただけです。

今までは沸騰直後のお湯をそのまま使っていましたが、少しだけ待ってから淹れてみると、味がまろやかになる気がしました。気のせいかもしれません。でも、そう感じられただけでも十分です。

* 朝起きたらまずカーテンを開ける
* コーヒーはゆっくり飲む（急がない）
* 5分だけでも机を片付ける
* スマホを見る前に深呼吸する
* 夜は照明を少し暗くする
* 「まあいっか」を1回は使う

### 朝の時間は、ほんの少しの変化で印象が変わります。

同じ豆、同じカップ、同じ部屋なのに、不思議なものです。

[Google](https://www.google.com)

![random image](https://fastly.picsum.photos/id/223/200/300.jpg?hmac=IZftr2PJy4auHpfBpLuMtFhsxgQYlUgXdV5rFwjGItQ)

こういう小さな実験を、**これから** もたまにやってみようと思います。

![random image 2](https://fastly.picsum.photos/id/361/200/300.jpg?hmac=unS_7uvpA3Q-hJTvI1xNCnlhta-oC6XnWZ4Y11UpjAo)
    """

    post_to_note(EMAIL, PASSWORD, TITLE, CONTENT, None)
