from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..db import init_db, list_dates, list_cards_by_label
from ..pipeline import yesterday_kst

app = FastAPI()
templates = Jinja2Templates(directory="src/dailypaper/web/templates")
app.mount("/static", StaticFiles(directory="src/dailypaper/web/static"), name="static")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    init_db()
    dates = list_dates(60)
    date = dates[0] if dates else yesterday_kst()
    buckets = list_cards_by_label(date)
    labels = sorted(buckets.keys())
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "date": date,
            "dates": dates,
            "labels": labels,
            "buckets": buckets,
        },
    )

@app.get("/d/{date}", response_class=HTMLResponse)
def by_date(date: str, request: Request):
    init_db()
    dates = list_dates(60)
    buckets = list_cards_by_label(date)
    labels = sorted(buckets.keys())
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "date": date,
            "dates": dates,
            "labels": labels,
            "buckets": buckets,
        },
    )
