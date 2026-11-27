import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sfs import research  # noqa: E402
from sfs.core import Store, load_settings  # noqa: E402


def make_number(base12: str) -> str:
    total = sum(int(d) * (1 if i % 2 == 0 else 2) for i, d in enumerate(reversed(base12)))
    return str(9 - total % 9) + base12


def rec(i: int = 1, **kw) -> dict:
    """テスト用の架空レコード（example.com。実在企業ではない）。"""
    r = {"corporate_number": make_number(f"{i:012d}"), "name": f"テスト株式会社{i}",
         "address": "東京都小金井市本町1-1-1", "city": "小金井市", "nearest_station": "武蔵小金井駅",
         "walk_minutes": 5, "employees": 80, "employees_as_of": "2026年4月",
         "employees_url": "https://example.com/company", "industry": "IT・システム開発",
         "business_summary": "受託開発", "website": f"https://example.com/{i}",
         "representative": "代表取締役 試験 太郎", "owner_managed": True, "owner_managed_basis": "創業者",
         "recruit_active": True, "recruit_info": "新卒・中途でエンジニア募集", "recruit_url": "https://example.com/r",
         "welfare_info": "退職金、確定拠出年金、住宅手当、資格取得支援", "welfare_url": "https://example.com/w",
         "health_mgmt": "健康経営優良法人2026", "retention_info": "平均勤続12年", "community_info": "未確認",
         "contact_department": "総務部", "contact_phone": "042-000-0000", "contact_email": "info@example.com",
         "contact_form_url": "https://example.com/contact", "sales_prohibited": False, "sns": [],
         "sources": [{"url": "https://example.com/company", "what": "会社概要"}], "verified_date": "2026-11-27"}
    r.update(kw)
    return r


@pytest.fixture
def settings():
    s = load_settings()
    s["compliance"]["agency_approved"] = False
    return s


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "state")


@pytest.fixture
def loaded(store, settings, tmp_path):
    import json
    p = tmp_path / "in.json"
    recs = [rec(1), rec(2, employees=None, employees_url="未確認"),
            rec(3, city="未確認"),
            rec(4, sales_prohibited=True, sales_prohibited_note="営業お断り", contact_email="未確認"),
            rec(5, city="札幌市"), rec(6, health_mgmt="未確認", welfare_info="未確認", recruit_active=False,
                                       recruit_info="未確認", retention_info="未確認", owner_managed=None,
                                       contact_department="未確認", industry="その他", employees=250)]
    p.write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
    research.import_files([p], store, settings)
    return store, p
