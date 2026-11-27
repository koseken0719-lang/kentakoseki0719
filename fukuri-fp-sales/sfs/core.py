"""設定・ログ・ローカル状態ストア・API利用上限。"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable

import yaml

from . import schema as S

ROOT = Path(__file__).resolve().parent.parent
SECRET_PAT = re.compile(r"(token|secret|password|api[_-]?key|authorization)\s*[=:]\s*\S+", re.I)


def load_settings(path: Path | None = None) -> dict:
    with open(path or ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_dotenv(path: Path | None = None) -> None:
    p = path or ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip())


class _Redact(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = SECRET_PAT.sub(r"\1=<redacted>", str(record.getMessage()))
        record.args = ()
        return True


def get_logger(name: str = "sfs", log_dir: Path | None = None) -> logging.Logger:
    lg = logging.getLogger(name)
    if lg.handlers:
        return lg
    lg.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    d = log_dir or ROOT / "logs"
    d.mkdir(parents=True, exist_ok=True)
    for h in (logging.StreamHandler(),
              logging.FileHandler(d / f"sfs_{dt.date.today():%Y%m}.log", encoding="utf-8")):
        h.setFormatter(fmt)
        h.addFilter(_Redact())
        lg.addHandler(h)
    return lg


def today() -> str:
    return dt.date.today().isoformat()


def short_hash(*parts: str, n: int = 10) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:n]


def is_unknown(v: Any) -> bool:
    return v is None or (isinstance(v, str) and v.strip() in ("", S.UNKNOWN))


def to_int(v: Any) -> int | None:
    if isinstance(v, bool) or is_unknown(v):
        return None
    try:
        return int(float(str(v).replace(",", "")))
    except ValueError:
        return None


class Store:
    """シート単位のローカル状態（data/state/<シート名>.json）。

    Googleスプレッドシートを正本とし、実行のたびに pull → 処理 → push する。
    行はヘッダー名をキーにした dict。upsert はキー列で冪等。
    """

    def __init__(self, state_dir: Path | None = None):
        self.dir = Path(state_dir or ROOT / "data" / "state")
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, sheet: str) -> Path:
        return self.dir / f"{sheet}.json"

    def read(self, sheet: str) -> list[dict]:
        p = self._path(sheet)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []

    def write(self, sheet: str, rows: Iterable[dict]) -> None:
        cols = S.SHEETS[sheet]
        clean = [{c: r.get(c, "") for c in cols} for r in rows]
        if sheet != S.CONSULT:
            guard_no_personal_data(sheet, clean)
        fd, tmp = tempfile.mkstemp(dir=self.dir, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self._path(sheet))

    def upsert(self, sheet: str, row: dict, keep: Iterable[str] = ()) -> str:
        """キー一致行があれば更新（keep列は既存値を優先）、なければ追加。'insert'/'update'を返す。"""
        keys = S.KEYS[sheet]
        rows = self.read(sheet)
        for i, r in enumerate(rows):
            if all(str(r.get(k, "")) == str(row.get(k, "")) for k in keys):
                # 「未確認」で既存の確認済み情報を上書きしない（人が補完した移動時間等を保持）
                merged = {**r, **{k: v for k, v in row.items()
                                  if not (is_unknown(v) and not is_unknown(r.get(k)))}}
                for c in keep:
                    if not is_unknown(r.get(c)):
                        merged[c] = r[c]
                rows[i] = merged
                self.write(sheet, rows)
                return "update"
        rows.append(row)
        self.write(sheet, rows)
        return "insert"

    # --- スプレッドシートとの受け渡し（2次元配列） ---
    def to_values(self, sheet: str) -> list[list]:
        cols = S.SHEETS[sheet]
        return [cols] + [[r.get(c, "") for c in cols] for r in self.read(sheet)]

    def from_values(self, sheet: str, values: list[list]) -> int:
        if not values:
            self.write(sheet, [])
            return 0
        header = [str(h) for h in values[0]]
        rows = []
        for v in values[1:]:
            if not any(str(x).strip() for x in v):
                continue
            rows.append({h: (v[i] if i < len(v) else "") for i, h in enumerate(header)})
        self.write(sheet, rows)
        return len(rows)


def guard_no_personal_data(sheet: str, rows: list[dict]) -> None:
    """個人の家計・保険相談内容が法人営業シートに混入するのを防ぐ。"""
    for r in rows:
        for c, v in r.items():
            if isinstance(v, str) and any(t in v for t in S.FORBIDDEN_PERSONAL_TERMS) \
                    and c in ("備考", "内容", "課題・ニーズ"):
                raise ValueError(
                    f"{sheet} の「{c}」に個人の相談内容と思われる語が含まれています。"
                    "個人情報は法人営業用シートに保存できません。")


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """月間のAPI呼び出し回数・概算費用の上限管理（data/state/api_usage.json）。"""

    def __init__(self, settings: dict, state_dir: Path | None = None):
        self.conf = settings.get("budget", {})
        self.path = Path(state_dir or ROOT / "data" / "state") / "api_usage.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def usage(self, month: str | None = None) -> dict:
        return self._load().get(month or today()[:7], {})

    def charge(self, api: str, calls: int = 1) -> None:
        month = today()[:7]
        data = self._load()
        m = data.setdefault(month, {})
        conf = self.conf.get(api, {})
        new_calls = m.get(api, {}).get("calls", 0) + calls
        if "max_calls" in conf and new_calls > conf["max_calls"]:
            raise BudgetExceeded(f"{api}: 月間呼び出し上限 {conf['max_calls']} 回を超えます")
        yen = lambda a, c: c * self.conf.get(a, {}).get("yen_per_call", 0)
        total = sum(yen(a, u["calls"]) for a, u in m.items() if a != api) + yen(api, new_calls)
        cap = self.conf.get("monthly_yen_cap")
        if cap is not None and total > cap:
            raise BudgetExceeded(f"月間API費用上限 {cap} 円を超えます（見込み {total:.0f} 円）")
        m[api] = {"calls": new_calls, "yen": yen(api, new_calls)}
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
