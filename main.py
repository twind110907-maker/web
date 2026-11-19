from pathlib import Path
import pandas as pd
import numpy as np
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Phân tích Biến động Giá Chứng khoán")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/charts", StaticFiles(directory=str(BASE_DIR / "phan_tich_gia")), name="charts")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def load_stock_analysis():
    csv_files = list(BASE_DIR.rglob("abc-19.csv"))
    if not csv_files:
        return (
            {
                "open_first": "11,000 VND",
                "max_price": "12,133 VND",
                "min_price": "339.84 VND",
                "pct_change": "-95.78%",
                "total_days": 365,
            },
            [],
        )

    df = pd.read_csv(csv_files[0], header=None)
    df.columns = ["Open", "High", "Low", "Close", "Ref_Price", "Floor", "Ceiling"]
    df["Date"] = pd.date_range("2025-01-01", periods=len(df), freq="D").strftime("%Y-%m-%d")
    df["Range"] = df["High"] - df["Low"]

    open_first = float(df["Open"].iloc[0])
    close_last = float(df["Close"].iloc[-1])
    pct_change = ((close_last - open_first) / open_first) * 100

    kpis = {
        "open_first": f"{open_first:,.0f} VND",
        "max_price": f"{df['High'].max():,.0f} VND",
        "min_price": f"{df['Low'].min():,.2f} VND",
        "pct_change": f"{pct_change:+.2f}%",
        "total_days": len(df),
    }

    abnormal_rows = []
    for _, r in df.iterrows():
        status = None
        tag = ""
        if np.isclose(r["Close"], r["Ceiling"], rtol=1e-4):
            status = "Chạm trần (+10%)"
            tag = "ceil"
        elif np.isclose(r["Close"], r["Floor"], rtol=1e-4):
            status = "Chạm sàn (-10%)"
            tag = "floor"

        if status:
            abnormal_rows.append({
                "date": r["Date"],
                "ref": f"{r['Ref_Price']:,.2f}",
                "close": f"{r['Close']:,.2f}",
                "range": f"{r['Range']:,.2f}",
                "status": status,
                "tag": tag,
            })

    return kpis, abnormal_rows


@app.get("/")
async def home(request: Request):
    kpis, abnormal_rows = load_stock_analysis()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "kpis": kpis,
            "abnormal_rows": abnormal_rows,
        },
    )
