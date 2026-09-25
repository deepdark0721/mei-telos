#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""telos_freshness_check.py — 个人画像保鲜检查（只读）。

画像文件建好后会自然变旧：占位符没填、变更记录停在月初、某文件整个缺失。
本脚本把「保鲜」从口头纪律变成可跑检查：扫 profile/ 下 8 个画像文件，
按日期阈值判定新鲜度，产出报告与优先修复清单。

检查项（每文件）
----------------
  MISSING         8 个预期文件缺了哪个                    major
  UNFILLED        仍有【你的XX】占位符（初版没填完）        major
  NO_CHANGELOG    无「## 变更记录」或无数据行              minor
  BAD_DATE        日期行无法解析（非 YYYY-MM-DD）           minor
  STALE           末次变更距今 >30 天（需刷新）             minor
  STALE_SEVERE    末次变更距今 >90 天（建议整份重审）       major

阈值来源：30 天标记需刷新、90 天低价值条目转归档的经验口径。
诚实边界：只看变更记录里的日期与占位符，推不出内容本身是否过时；
判断「内容还准不准」仍要你自己过一遍。只读，不修改任何画像文件。

用法：
  python telos_freshness_check.py                     # 扫当前目录下 profile/
  python telos_freshness_check.py --profile-dir D:\\telos\\profile
  python telos_freshness_check.py --today 2026-10-01 --json
  python telos_freshness_check.py --selftest
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

EXPECTED = (
    "identity.md", "goals.md", "interests.md", "skills.md",
    "beliefs.md", "learned.md", "soul.md", "work-style.md",
)
STALE_DAYS = 30
SEVERE_DAYS = 90
# 仓库约定：【】= 待替换占位符（含【你的XX】与【如：…】提示形）
PLACEHOLDER_RE = re.compile(r"【[^】]+】")
# 宽捕日期形首格（含 2026/08/01 等错格式），解析失败即 BAD_DATE
DATE_CELL_RE = re.compile(r"^\|\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\s*\|")
CHANGELOG_HEAD_RE = re.compile(r"^##\s*.*变更记录", re.M)


def _parse_date(s: str):
    try:
        return _dt.date.fromisoformat(s)
    except ValueError:
        return None


def check_text(text: str, path: Path, today: _dt.date) -> list:
    findings = []
    name = path.name

    def add(kind, severity, msg):
        findings.append({"file": name, "kind": kind,
                         "severity": severity, "msg": msg})

    ph = PLACEHOLDER_RE.findall(text)
    if ph:
        uniq = sorted(set(ph))
        shown = "、".join(uniq[:3]) + ("等" if len(uniq) > 3 else "")
        add("UNFILLED", "major",
            f"仍有 {len(ph)} 处占位符未填（{shown}）")

    if not CHANGELOG_HEAD_RE.search(text):
        add("NO_CHANGELOG", "minor", "缺少「## 变更记录」小节")
        return findings

    last, bad = None, 0
    in_table = False
    for line in text.splitlines():
        if CHANGELOG_HEAD_RE.search(line):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            in_table = False
        if not in_table:
            continue
        m = DATE_CELL_RE.match(line.strip())
        if not m:
            continue
        d = _parse_date(m.group(1))
        if d is None:
            bad += 1
        elif last is None or d > last:
            last = d

    if bad:
        add("BAD_DATE", "minor", f"{bad} 行日期无法解析（应为 YYYY-MM-DD）")
    if last is None:
        add("NO_CHANGELOG", "minor", "变更记录里没有可解析的数据行")
        return findings

    age = (today - last).days
    if age > SEVERE_DAYS:
        add("STALE_SEVERE", "major",
            f"末次变更 {last.isoformat()}，已 {age} 天，建议整份重审")
    elif age > STALE_DAYS:
        add("STALE", "minor",
            f"末次变更 {last.isoformat()}，已 {age} 天，该刷新了")
    return findings


def scan(profile_dir: Path, today: _dt.date) -> dict:
    findings = []
    warnings = []
    for name in EXPECTED:
        p = profile_dir / name
        if not p.is_file():
            findings.append({"file": name, "kind": "MISSING", "severity": "major",
                             "msg": "预期画像文件缺失"})
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            warnings.append(f"无法读取 {p}: {exc}")
            continue
        findings.extend(check_text(text, p, today))

    by_sev = {"major": 0, "minor": 0}
    for f in findings:
        by_sev[f["severity"]] += 1
    status = "CRITICAL" if by_sev["major"] else (
        "WARNING" if by_sev["minor"] or warnings else "OK")
    return {
        "profile_dir": str(profile_dir),
        "today": today.isoformat(),
        "files_expected": len(EXPECTED),
        "findings": findings,
        "warnings": warnings,
        "by_severity": by_sev,
        "status": status,
    }


def to_markdown(rep: dict) -> str:
    lines = [
        "telos 画像保鲜检查 — " + rep["today"],
        "profile: " + rep["profile_dir"],
        "",
        f"状态: {rep['status']}  major={rep['by_severity']['major']}"
        f"  minor={rep['by_severity']['minor']}",
        "",
    ]
    if rep["findings"]:
        lines.append("| 文件 | 级别 | 问题 | 动作 |")
        lines.append("|------|------|------|------|")
        order = {"MISSING": "补建该文件",
                 "UNFILLED": "填掉占位符",
                 "NO_CHANGELOG": "补变更记录表",
                 "BAD_DATE": "修正日期格式",
                 "STALE": "补一条变更记录",
                 "STALE_SEVERE": "整份过一遍并更新"}
        for f in sorted(rep["findings"],
                        key=lambda x: (x["severity"] != "major", x["file"])):
            lines.append(f"| {f['file']} | {f['severity']} | "
                         f"{f['kind']}: {f['msg']} | {order.get(f['kind'], '')} |")
    else:
        lines.append("8 个画像文件齐全，占位符已填，变更记录都在阈值内。")
    for w in rep["warnings"]:
        lines.append(f"\n警告: {w}")
    return "\n".join(lines)


def _selftest() -> int:
    today = _dt.date(2026, 10, 1)
    cases = [
        ("缺失", {}, "MISSING"),
        ("占位符", {"body": "## 变更记录\n| 2026-09-30 | 建立 | 本人 |\n\n【你的学校】",
                    "name": "identity.md"}, "UNFILLED"),
        ("新鲜", {"body": "## 变更记录\n| 2026-09-30 | 更新状态 | 本人 |\n\n正文",
                  "name": "goals.md"}, None),
        ("需刷新", {"body": "## 变更记录\n| 2026-08-01 | 更新 | 本人 |\n\n正文",
                    "name": "skills.md"}, "STALE"),
        ("严重过期", {"body": "## 变更记录\n| 2026-01-01 | 更新 | 本人 |\n\n正文",
                      "name": "soul.md"}, "STALE_SEVERE"),
        ("坏日期", {"body": "## 变更记录\n| 2026/08/01 | 更新 | 本人 |\n\n正文",
                    "name": "beliefs.md"}, "BAD_DATE"),
    ]
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for label, spec, expect in cases:
            if spec == {}:
                rep = scan(root, today)
                kinds = [f["kind"] for f in rep["findings"]]
                hit = "MISSING" in kinds
            else:
                p = root / spec["name"]
                p.write_text(spec["body"], encoding="utf-8")
                findings = check_text(spec["body"], p, today)
                kinds = [f["kind"] for f in findings]
                hit = expect in kinds if expect else not kinds
            mark = "PASS" if hit else "FAIL"
            if not hit:
                ok = False
            print(f"{mark}  {label}: got={kinds}")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="telos 画像保鲜检查（只读）")
    ap.add_argument("--profile-dir", default=None,
                    help="画像目录（默认：脚本所在目录上级的 profile/）")
    ap.add_argument("--today", help="基准日期 YYYY-MM-DD（默认今天，可复现）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--selftest", action="store_true", help="跑内置用例")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.today:
        y, m, d = args.today.split("-")
        today = _dt.date(int(y), int(m), int(d))
    else:
        today = _dt.date.today()

    if args.profile_dir:
        profile = Path(args.profile_dir)
    else:
        profile = Path(__file__).resolve().parent.parent / "profile"
    if not profile.is_dir():
        print(f"画像目录不存在: {profile}", file=sys.stderr)
        return 2

    rep = scan(profile, today)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(to_markdown(rep))
    return 1 if rep["by_severity"]["major"] else 0


if __name__ == "__main__":
    sys.exit(main())
