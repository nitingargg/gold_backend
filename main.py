from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date
import requests
import bs4
from pymongo import MongoClient
from contextlib import asynccontextmanager

class RateModel(BaseModel):
    gold_cash: int
    gold_rtgs: int
    silver_cash: int
    silver_rtgs: int

ATLAS_URI = "mongodb+srv://ngargq:JY8X9Iu7zbhGwqaw@cluster0.2uwod.mongodb.net/"
DB_NAME = "sai_gold_data"
COLLECTION = "differences"

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.mongodb_client = MongoClient(ATLAS_URI)
    app.database = app.mongodb_client[DB_NAME]
    app.collection = app.database[COLLECTION]
    print("Connected to the MongoDB database!")
    yield
    app.mongodb_client.close()
    print("Database Connection Closed!")

app = FastAPI(lifespan=lifespan)

def get_MCX():
    html = requests.get("https://mcxlive.org/", headers={'Cache-Control': 'no-cache'})
    soup = bs4.BeautifulSoup(html.text, 'html.parser')
    data = soup.find("table", class_="main-table")
    rows = data.find_all("tr")
    gold_row = rows[1]
    gold = gold_row.find("td", class_="index-rates").text.strip().split(",")
    gold = float("".join(map(str,gold)))
    silver_row = rows[2]
    silver = silver_row.find("td", class_="index-rates").text.strip().split(",")
    silver = float("".join(map(str,silver)))
    return gold,silver


@app.get("/")
def home():
    return {"Message": "API is Up and Running!"}

# @app.get("/get_rate")
# def get_rate():
#     gold, silver = get_MCX()
#     return {"goldMCX":gold, "silverMCX":silver}

@app.post("/set_differences")
def create_price(price: RateModel):
    try:
        price_dict = price.model_dump()
        price_dict["date"] = date.today().isoformat()
        already = app.collection.find_one({"date": date.today().isoformat()})
        if already:
            app.collection.update_one({"date": date.today().isoformat()}, {"$set":price_dict})
            return {"Message": "Updated"}
        else:
            result = app.collection.insert_one(price_dict)
            return {"Message": "Inserted"}
    except Exception as e:
        print(e)
        return HTTPException(400, "Some Error Occured! Check Logs")

# @app.get("/get_differences")
# def get_price():
#     entry = app.collection.find_one({"date": date.today().isoformat()})
#     if(entry):
#         return {"gold_cash": entry["gold_cash"],"silver_cash": entry["silver_cash"],"gold_rtgs": entry["gold_rtgs"],"silver_rtgs": entry["silver_rtgs"]}
#     else:
#         HTTPException(404, "Not Found Today's Entry")

@app.get("/get_data")
def get_data():
    try:
        gold, silver = get_MCX()
        entry = app.collection.find_one(sort=[('$natural', -1)])
        if(entry):
            return {"gold_cash": entry["gold_cash"],"silver_cash": entry["silver_cash"],"gold_rtgs": entry["gold_rtgs"],"silver_rtgs": entry["silver_rtgs"],
                "gold_mcx":gold, "silver_mcx":silver}
        else:
            return HTTPException(400, "Not Found Any Entry")
    except Exception as e:
        print(e)
        return HTTPException(400, "Some Error Occured! Check Logs")

