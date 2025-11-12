import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId

# Database helpers
from database import db, create_document, get_documents

app = FastAPI(title="E-Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductIn(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    image: Optional[str] = Field(None, description="Product image URL")
    in_stock: bool = Field(True, description="Whether product is in stock")


class ProductOut(ProductIn):
    id: str


@app.get("/")
def read_root():
    return {"message": "E-Commerce Backend is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Utility to convert Mongo documents to ProductOut

def _doc_to_product(doc) -> ProductOut:
    return ProductOut(
        id=str(doc.get("_id")),
        title=doc.get("title"),
        description=doc.get("description"),
        price=float(doc.get("price", 0)),
        category=doc.get("category"),
        image=doc.get("image"),
        in_stock=bool(doc.get("in_stock", True)),
    )


@app.get("/api/products", response_model=List[ProductOut])
def list_products(category: Optional[str] = None, limit: int = 50):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    filt = {"category": category} if category else {}
    docs = get_documents("product", filt, limit)
    return [_doc_to_product(d) for d in docs]


@app.post("/api/products", response_model=str)
def create_product(product: ProductIn):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    new_id = create_document("product", product.dict())
    return new_id


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")
    doc = db["product"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return _doc_to_product(doc)


@app.post("/api/seed", response_model=int)
def seed_products():
    """Quickly seed demo products if the collection is empty."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    if db["product"].count_documents({}) > 0:
        return 0
    demo = [
        {
            "title": "NeoCube Pro",
            "description": "Futuristic modular cube speaker with reactive LEDs.",
            "price": 199.99,
            "category": "audio",
            "image": "https://images.unsplash.com/photo-1518779578993-ec3579fee39f?auto=format&fit=crop&w=800&q=60",
            "in_stock": True,
        },
        {
            "title": "Iris Orbit Lamp",
            "description": "Iridescent smart lamp that orbits hues through the day.",
            "price": 129.0,
            "category": "lighting",
            "image": "https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?auto=format&fit=crop&w=800&q=60",
            "in_stock": True,
        },
        {
            "title": "Glyph Headphones",
            "description": "Metallic over-ears with spatial audio and ANC.",
            "price": 249.0,
            "category": "audio",
            "image": "https://images.unsplash.com/photo-1518443747120-6f6f2d80b7a1?auto=format&fit=crop&w=800&q=60",
            "in_stock": True,
        },
        {
            "title": "Prism Desk Mat",
            "description": "Soft-touch mat with subtle neon edge glow.",
            "price": 39.0,
            "category": "accessories",
            "image": "https://images.unsplash.com/photo-1473186578172-c141e6798cf4?auto=format&fit=crop&w=800&q=60",
            "in_stock": True,
        },
    ]
    inserted = 0
    for d in demo:
        create_document("product", d)
        inserted += 1
    return inserted


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
