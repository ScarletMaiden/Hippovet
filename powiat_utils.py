import re
import pandas as pd
import pgeocode

_nomi = pgeocode.Nominatim("PL")

def _normalize_kod(kod: str) -> str:
    if kod is None:
        return ""
    s = re.sub(r"\D", "", str(kod))
    if len(s) == 5:
        return f"{s[:2]}-{s[2:]}"
    return str(kod).strip()

def powiat_from_postal(kod: str) -> str:
    k = _normalize_kod(kod)
    if not k or str(k).strip().lower() in ("nan", "none"):
        return ""
    try:
        rec = _nomi.query_postal_code(k)
        powiat = getattr(rec, "county_name", None)
        if powiat is None or (isinstance(powiat, float) and pd.isna(powiat)) or str(powiat).strip() == "":
            powiat = getattr(rec, "community_name", "") or ""
        return str(powiat) if powiat else ""
    except Exception:
        return ""

def _find_col(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def fill_powiat_auto(df: pd.DataFrame, powiat_col: str = "Powiat", kod_candidates=("Kod-pocztowy", "Kod-pocztowy ")):
    if powiat_col not in df.columns:
        df[powiat_col] = pd.NA

    kod_col = _find_col(df, kod_candidates)
    if kod_col is None:
        return df, 0, None

    filled = 0
    for i in df.index:
        cur_pow_val = df.at[i, powiat_col] if powiat_col in df.columns else pd.NA
        cur_pow_empty = pd.isna(cur_pow_val) or str(cur_pow_val).strip().lower() in ("", "nan", "none")

        if cur_pow_empty:
            kod_val = df.at[i, kod_col] if kod_col in df.columns else pd.NA
            kod_empty = pd.isna(kod_val) or str(kod_val).strip().lower() in ("", "nan", "none")
            if not kod_empty:
                k = str(kod_val).strip()
                df.at[i, powiat_col] = powiat_from_postal(k)
                filled += 1

    return df, filled, kod_col
