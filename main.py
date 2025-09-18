from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
import models, schemas, database, auth

models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://visionary-meerkat-b6233d.netlify.app/"],  # Vite default is 5173, CRA is 3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/signup", response_model=schemas.User)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = auth.hash_password(user.password)
    new_user = models.User(email=user.email, name=user.name, password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth.create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/blogs", response_model=schemas.Blog)
def create_blog(blog: schemas.BlogCreate, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    new_blog = models.Blog(title=blog.title, content=blog.content, author_id=current_user.id)
    db.add(new_blog)
    db.commit()
    db.refresh(new_blog)
    return new_blog

@app.get("/blogs", response_model=list[schemas.Blog])
def get_blogs(db: Session = Depends(get_db)):
    return db.query(models.Blog).all()

@app.get("/blogs/{blog_id}", response_model=schemas.Blog)
def get_blog(blog_id: int, db: Session = Depends(get_db)):
    blog = db.query(models.Blog).filter(models.Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    return blog

@app.delete("/blogs/{blog_id}")
def delete_blog(blog_id: int, db: Session = Depends(get_db), current_user=Depends(auth.get_current_user)):
    blog = db.query(models.Blog).filter(models.Blog.id == blog_id, models.Blog.author_id == current_user.id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Not found or not your blog")
    db.delete(blog)
    db.commit()
    return {"msg": "Blog deleted"}

@app.get("/me", response_model=schemas.User)
def get_profile(current_user=Depends(auth.get_current_user)):
    return current_user