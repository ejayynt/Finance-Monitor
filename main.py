from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import csv
import os
from datetime import datetime

app = FastAPI()

# --- PATH SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
DATA_FILE = os.path.join(BASE_DIR, "expenses.csv")

if not os.path.exists(TEMPLATE_DIR):
    print(f"CRITICAL ERROR: 'templates' folder not found at {TEMPLATE_DIR}")

templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Ensure CSV exists with headers
if not os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "date",
                    "category",
                    "subcategory",
                    "amount",
                    "surcharge",
                    "necessity",
                    "desc",
                ]
            )
    except PermissionError:
        print(f"ERROR: Cannot create {DATA_FILE}. Is it open in Excel?")


# --- Data Validation ---
class ExpenseModel(BaseModel):
    date: str
    category: str
    subcategory: str
    amount: float
    surcharge: Optional[float] = 0.0
    necessity: str
    desc: str


def clean_date(date_str):
    """Standardize dates to YYYY-MM-DD"""
    if not date_str or date_str == "date":
        return None
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.today().strftime("%Y-%m-%d")


# --- ROUTES ---


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/expenses")
async def get_expenses():
    results = []
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                # Enumerate adds a temporary ID based on row index
                for idx, row in enumerate(reader):
                    if not row or not row.get("date"):
                        continue
                    row["date"] = clean_date(row["date"])
                    row["id"] = idx
                    results.append(row)
    except PermissionError:
        return JSONResponse(
            status_code=500, content={"message": "File is open in Excel."}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
    return results


@app.post("/api/expenses")
async def add_expense(expense: ExpenseModel):
    clean_dt = clean_date(expense.date)
    try:
        with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    clean_dt,
                    expense.category,
                    expense.subcategory,
                    expense.amount,
                    expense.surcharge,
                    expense.necessity,
                    expense.desc,
                ]
            )
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


@app.delete("/api/expenses/{row_id}")
async def delete_expense(row_id: int):
    """Deletes a specific row by index and rewrites the CSV"""
    try:
        rows = []
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            rows = list(csv.reader(f))

        # Row 0 is header. Data starts at 1.
        target_index = row_id + 1

        if 1 <= target_index < len(rows):
            del rows[target_index]

            # Rewrite file
            with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            return {"status": "deleted"}
        else:
            return JSONResponse(status_code=404, content={"message": "ID not found"})

    except PermissionError:
        return JSONResponse(
            status_code=500, content={"message": "File is open in Excel."}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})
