# weekly_aggregate.py
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd

OUTPUT_DIR = Path("output")
WEEKLY_DIR = OUTPUT_DIR / "weekly"
WEEKLY_DIR.mkdir(parents=True, exist_ok=True)

def daily_file_for(d):
    return OUTPUT_DIR / f"news_{d.strftime('%Y-%m-%d')}.csv"

def normalize_pub_date(df):
    if "pub_date" in df.columns:
        # 统一为 UTC aware，避免 sort 时类型冲突
        df["pub_date"] = pd.to_datetime(df["pub_date"], utc=True, errors="coerce")
    return df

def aggregate_last_week():
    # 周一执行时，把“上一周（周一~周日）”做汇总
    today_utc = datetime.now(timezone.utc).date()
    # 计算上一周的周一与周日（ISO: Monday=1 ... Sunday=7）
    iso = today_utc.isocalendar()
    # 本周一
    this_monday = today_utc - timedelta(days=iso.weekday - 1)
    # 上周一、上周日
    last_monday = this_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)

    # 收集文件
    files = []
    d = last_monday
    while d <= last_sunday:
        f = daily_file_for(d)
        if f.exists():
            files.append(f)
        d += timedelta(days=1)

    if not files:
        # 写个空表，保证流程不断
        empty = pd.DataFrame(columns=["title", "link", "published", "source", "pub_date"])
        out = WEEKLY_DIR / f"news_week_{last_sunday.isocalendar().year}-W{last_sunday.isocalendar().week:02d}.csv"
        empty.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"Weekly aggregate: 0 records → {out}")
        return

    # 读取并合并
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            df = normalize_pub_date(df)
            dfs.append(df)
        except Exception as e:
            print(f"Skip {f} due to error: {e}")

    if not dfs:
        empty = pd.DataFrame(columns=["title", "link", "published", "source", "pub_date"])
        out = WEEKLY_DIR / f"news_week_{last_sunday.isocalendar().year}-W{last_sunday.isocalendar().week:02d}.csv"
        empty.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"Weekly aggregate: 0 records → {out}")
        return

    all_df = pd.concat(dfs, ignore_index=True)

    # 去重策略：优先按标准化标题，必要时叠加 link
    all_df["title_norm"] = all_df.get("title", "").fillna("").astype(str).str.strip()
    subset_cols = ["title_norm"]  # 可换成 ["title_norm", "link"] 提升鲁棒性

    # 排序 + 去重（保留最早）
    if "pub_date" in all_df.columns:
        all_df = all_df.sort_values(by="pub_date", ascending=True)

    dedup = all_df.drop_duplicates(subset=subset_cols, keep="first").drop(columns=["title_norm"])

    # 输出名：按 ISO 周
    iso_last = last_sunday.isocalendar()
    out = WEEKLY_DIR / f"news_week_{iso_last.year}-W{iso_last.week:02d}.csv"
    dedup.to_csv(out, index=False, encoding="utf-8-sig")

    print(f"Weekly aggregate: {len(dedup)} records from {len(files)} files → {out}")
    print(f"Window: {last_monday} to {last_sunday} (UTC dates)")

if __name__ == "__main__":
    aggregate_last_week()
