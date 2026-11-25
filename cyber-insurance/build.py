"""data/*.json を template.html に埋め込んで index.html を生成する。

使い方: python3 cyber-insurance/build.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent

ROWS = [
    {"group": "基本情報"},
    {"key": "target", "label": "対象・販売形態"},
    {"key": "revision", "label": "最新改定"},
    {"group": "① 賠償責任の補償"},
    {"key": "overview", "label": "賠償責任に関する補償"},
    {"key": "liability_limit", "label": "填補限度額（賠償責任）", "note": "最大"},
    {"key": "ip_infringement", "label": "知的財産権等侵害の賠償責任"},
    {"key": "cyber_bodily_property", "label": "サイバー起因の対人・対物事故"},
    {"group": "② 事故対応費用"},
    {"key": "incident_response_limit", "label": "填補限度額（事故対応費用）", "note": "最大"},
    {"key": "forensic_internal", "label": "フォレンジック発動要件：社内発見", "note": "サイバー攻撃のおそれを社内で認識", "hl": True},
    {"key": "forensic_public_vendor", "label": "フォレンジック発動要件：公的機関・委託ベンダーからの通報", "hl": True},
    {"key": "forensic_third_party", "label": "フォレンジック発動要件：その他第三者からの通報", "note": "取引先・クレジットカード会社等", "hl": True},
    {"key": "system_restoration", "label": "コンピュータシステム復旧費用"},
    {"key": "mimaikin", "label": "見舞金・見舞品購入費用"},
    {"key": "recurrence_prevention", "label": "再発防止費用"},
    {"key": "litigation", "label": "訴訟対応費用", "note": "意見書・鑑定書の作成費用等"},
    {"group": "③ 自社の損害・その他"},
    {"key": "business_interruption", "label": "利益損害・営業継続費用"},
    {"key": "ransom_or_other", "label": "その他の特徴的な補償", "note": "身代金・不正送金等"},
    {"key": "services", "label": "付帯サービス"},
    {"group": "資料"},
    {"key": "pamphlet", "label": "パンフレット等", "docs": True},
    {"key": "yakkan", "label": "約款・特約", "docs": True},
    {"key": "product_page_url_docs", "label": "商品ページ", "docs": True},
]


def main():
    products = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))
    news = json.loads((ROOT / "data/news.json").read_text(encoding="utf-8"))
    for p in products["products"]:
        url = p.get("product_page_url")
        p["product_page_url_docs"] = [{"title": "公式ページ", "url": url}] if url else []
    data = {
        "checked_at": products["checked_at"],
        "changes": products.get("changes", []),
        "products": products["products"],
        "rows": ROWS,
        "news": news["categories"],
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (ROOT / "template.html").read_text(encoding="utf-8").replace("/*__DATA__*/", payload)
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote index.html ({len(html):,} bytes, {len(products['products'])} products)")


if __name__ == "__main__":
    main()
