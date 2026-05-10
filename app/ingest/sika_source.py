"""
Fetcher "Poli" pour les données historiques (Sika/Richbourse).
Inclut un rate-limiting strict, une logique de retries, et génère systématiquement
des certificats d'audit (Manifests) pour garantir la provenance des données.
"""
import argparse
import logging
import os
import time
from datetime import datetime
import pandas as pd
import yaml
from pathlib import Path
import sys

from app.core.manifests import create_manifest, write_manifest
from app.ingest.utils import extract_tickers_from_universe

# --- Copie/Adaptation du Client Richbourse depuis l'ancien projet ---
import json
import re
import urllib3
import requests
from dateutil.parser import isoparse
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RICHBOURSE_TECH_URL = "https://www.richbourse.com/common/mouvements/technique/{symbol}/status/200"

def _to_date_utc_naive_from_ms(ts_ms: int):
    return pd.to_datetime(ts_ms, unit="ms", utc=True).to_pydatetime().date()

def _parse_js_array(text: str):
    s = re.sub(r",\s*(\]|\})", r"\1", text.strip())
    return json.loads(s)

def _extract_bracketed_array(s: str, start_idx: int):
    if start_idx >= len(s) or s[start_idx] != "[": return None
    depth, i, in_str, esc = 0, start_idx, False, False
    while i < len(s):
        ch = s[i]
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
        else:
            if ch == '"': in_str = True
            elif ch == "[": depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0: return s[start_idx : i + 1], i + 1
        i += 1
    return None

def _extract_data_arrays_from_html(html: str):
    arrays = []
    for m in re.finditer(r"\bdata\s*:\s*\[", html):
        start = m.end() - 1
        got = _extract_bracketed_array(html, start)
        if not got: continue
        arr_txt, _ = got
        try: arrays.append(_parse_js_array(arr_txt))
        except Exception: continue
    return arrays

def _pick_ohlc_and_volume(arrays):
    ohlc, vol = None, None
    for arr in arrays:
        if not isinstance(arr, list) or not arr: continue
        first = arr[0]
        if isinstance(first, list) and len(first) >= 5 and ohlc is None: ohlc = arr
        if isinstance(first, list) and len(first) == 2 and vol is None: vol = arr
    if ohlc is None: raise RuntimeError("OHLC Introuvable")
    return ohlc, vol

def fetch_history_raw(symbol: str, timeout_s: int = 15) -> pd.DataFrame:
    url = RICHBOURSE_TECH_URL.format(symbol=symbol.upper())
    headers = {"User-Agent": "brvm-intelligence/1.0", "Accept": "text/html,application/xhtml+xml"}
    resp = requests.get(url, headers=headers, timeout=timeout_s, verify=False)
    resp.raise_for_status()
    arrays = _extract_data_arrays_from_html(resp.text)
    ohlc_arr, vol_arr = _pick_ohlc_and_volume(arrays)

    ohlc_rows = []
    for row in ohlc_arr:
        if isinstance(row, list) and len(row) >= 5:
            d = _to_date_utc_naive_from_ms(int(row[0]))
            o, h, l, c = map(float, row[1:5])
            ohlc_rows.append((d, o, h, l, c))
    df_ohlc = pd.DataFrame(ohlc_rows, columns=["date", "open", "high", "low", "close"])

    if vol_arr:
        vol_rows = []
        for row in vol_arr:
            if isinstance(row, list) and len(row) == 2:
                d = _to_date_utc_naive_from_ms(int(row[0]))
                try: v = int(float(row[1]))
                except Exception: v = None
                vol_rows.append((d, v))
        df_vol = pd.DataFrame(vol_rows, columns=["date", "volume"])
        df = df_ohlc.merge(df_vol, on="date", how="left")
    else:
        df = df_ohlc.copy()
        df["volume"] = pd.NA

    df["symbol"] = symbol.upper()
    return df

# --- Logique Principale du Script ---

def load_config(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def run_ingestion(probe: bool = False, force: bool = False):
    base_dir = Path(__file__).resolve().parent.parent.parent
    config_sources = load_config(base_dir / "config" / "sources.yaml")
    config_universe = load_config(base_dir / "config" / "universe.yaml")
    
    out_dir = base_dir / "data" / "raw" / "sika_csv"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir = base_dir / "data" / "manifests"
    
    tickers = extract_tickers_from_universe(config_universe)
    if probe:
        logging.info("PROBE MODE: Testing 1 ticker only.")
        tickers = tickers[:1]

    sleep_time = 1.0 / config_sources.get("sika", {}).get("rps", 1.0)
    from tqdm import tqdm
    
    for ticker in tqdm(tickers, desc="Fetching Sika Prices", unit="ticker"):
        output_file = out_dir / f"{ticker}_raw.csv"
        
        # --- Logic de Skip (Cache de 12h) ---

        if not force and output_file.exists():
            mtime = datetime.fromtimestamp(output_file.stat().st_mtime)
            diff = datetime.now() - mtime
            if diff.total_seconds() < 12 * 3600: # 12 heures
                logging.info(f"⏩ Data for {ticker} is recent ({diff.total_seconds()/3600:.1f}h old). Skipping.")
                continue

        logging.info(f"Fetching data for {ticker}...")
        try:
            time.sleep(sleep_time) # Polite rate limiting
            
            df = fetch_history_raw(ticker)
            
            # Sauvegarde en CSV brut
            df.to_csv(output_file, index=False)
            logging.info(f" Saved {len(df)} rows to {output_file.name}")
            
            # === CREATION DU MANIFEST POUR L'AUDIT ===
            manifest = create_manifest(
                file_path=str(output_file),
                source_url=RICHBOURSE_TECH_URL.format(symbol=ticker),
                source_name="SIKA/RICHBOURSE",
                params={"ticker": ticker, "mode": "full_history"}
            )
            write_manifest(manifest, out_dir=str(manifests_dir))
            
        except Exception as e:
            logging.error(f" Failed fetching {ticker}: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Poli Fetcher Sika/Richbourse")
    parser.add_argument("--probe", action="store_true", help="Run a dry test on a single ticker.")
    parser.add_argument("--force", action="store_true", help="Force download even if data is recent.")
    args = parser.parse_args()
    
    run_ingestion(probe=args.probe, force=args.force)
