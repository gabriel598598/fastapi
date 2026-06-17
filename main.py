
import os
from fastapi import FastAPI, Query, Body, HTTPException, Path, status, Depends
from pydantic import BaseModel, Field, field_validator, EmailStr, ConfigDict
from typing import Optional, List, Union, Literal
from math import ceil
from datetime import datetime                                                                                                           
from sqlalchemy import create_engine, Integer, String, Text, DateTime, select, func, UniqueConstraint, ForeignKey, Table, Column
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./blog.db")

print("conectado a :", DATABASE_URL)
engine_kwargs= {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"]={"check_same_thread": False}

engine = create_engine(DATABASE_URL, echo = True, future= True, **engine_kwargs)
session_local = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, class_=Session)

class Base(DeclarativeBase):
    pass

post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id",ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id",ondelete="CASCADE"), primary_key=True),
)
class AutorORM(Base):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[int] = mapped_column(String(100), nullable=False, index=True)
    email: Mapped[int] = mapped_column(String(100), unique=False, index=True)

    posts: Mapped[list["PostORM"]] = relationship(back_populates="author")#cambio


class TagORM(Base):
    __tablename__ ="tags"

    id : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, index=True)

    posts: Mapped[List["PostORM"]]= relationship(
        secondary=post_tags,
        back_populates="tags",
        lazy="selectin"
    )
     
class PostORM(Base):
    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("title",name="unique_post_title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at:Mapped[DateTime] = mapped_column(
        DateTime, default=datetime.utcnow)

    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("authors.id"))
    autor: Mapped[Optional["AutorORM"]]= relationship(back_populates="posts")

    tags: Mapped[List["TagORM"]] = relationship(
        secondary = post_tags,
        back_populates="posts",
        lazy="selectin", 
        passive_deletes=True
    )


Base.metadata.create_all(bind=engine)  #dev


def get_db():
    db = session_local()
    try:
        yield db 
    finally:
        db.close()

app = FastAPI(title="Mini Blog")




class Tag(BaseModel):
    name: str = Field(..., min_length=2, max_length=30, description="nombre de la etiqueta")
    model_config = ConfigDict(from_attributes=True)

class Author(BaseModel):
    name:str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)


class PostBase(BaseModel):
    title: str
    content: str
    tags: Optional[List[Tag]] = Field(default_factory=list)
    author: Optional[Author] = None
    model_config = ConfigDict(from_attributes=True)

class PostCreate(BaseModel):
    title: str = Field(
        ..., 
        min_length=3,
        max_length=100,
        description="titulo del post min 3 caracteres, max 100)",
        examples=["mi primer post con fastapi"]
    )
    content: Optional[str] = Field(
        default = "contenido no disponible",
        min_length= 10,
        description ="contenido del post min 10 caracteres",
        examples= [" este es un contenido valido ya que contiene 10 caracteres o mas"]


    ) 
    tags:List[Tag] = Field(default_factory=list)
    author: Optional[Author] = None
    
    @field_validator("title")
    @classmethod
    def not_allowed_title(cls, value:str) -> str:
        palabras={"ahora", "oso", "casa", "gato", "spam"}
        for palabra in palabras:
            if palabra  in value.lower():
                raise ValueError(f"no puede contener la palabra:{palabra}")
        return value

class PostPublic(PostBase):
    id: int
    #title: str
   # content: str

    model_config = ConfigDict(from_attributes=True)
   

class PostSummary(BaseModel):
    id: int
    title: str
    model_config = ConfigDict(from_attributes=True)

class paginatedPost(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    has_prev: bool
    has_next: bool
    order_by: Literal["id", "title"]
    direction: Literal["asc", "desc"]
    search: Optional[str] = None
    items: List[PostPublic]
    


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100)
    content: Optional[str] = None
    




@app.get("/")
def home():
    return{'message': 'bienvenidos'}


@app.get("/posts", response_model = paginatedPost)
def list_posts(\
  
    text: Optional [str ] = Query(
    default=None, 
    deprecated=True,
    description= "parametro obsoleto, usa search",
  
    ),
    
    query: Optional [str ] = Query(
    default=None, 
    description= "buscar titul0",
    alias="search", 
    min_length= 3,
    max_length= 100,
    pattern=r"^[\w\sáéíóúÁÉÍÓÚ-]+$"
    ),
        per_page: int = Query(
            10, ge=1, le=50,
            description="numero de resultado del 1 al 50"
    ),
        page: int = Query(
            1, ge=1,
            description="Numero de pagina >=1"
    ),
        order_by:Literal["id", "title"] = Query(
            "id", description="campo de orden"
        ),
        direction: Literal["asc", "desc"] = Query(
            "asc", description="direccion de orden"
        ),
        db:Session = Depends(get_db)
    ):
        results = select(PostORM)

        query = query or text
        if query:
            results = results.where(PostORM.title.ilike(f"%{query}%"))
            
        total = db.scalar(select(func.count()).select_from(
            results.subquery()))  or 0

        total_pages = ceil( total/per_page) if total > 0 else 0
        current_page = 1 if total_pages == 0 else min(page, total_pages)

        if total_pages == 0:
            current_page =1
        else :
            current_page = min(page, total_pages)

        if order_by == "id":
            order_col = PostORM.id
        else:
            order_col = func.lower(PostORM.title)

        results = results.order_by(order_col.asc() if direction == "asc" else order_col.desc())
        #results=sorted(
        #   results, key=lambda post: post[order_by], reverse=(direction== "desc" ))
        if total_pages == 0:
            items =list[PostORM] = []
        else:
            start = (current_page -1)* per_page
            items = db.execute(results.limit(per_page).offset(start)).scalars().all()

        has_prev = current_page > 1
        has_next = current_page < total_pages if total_pages > 0 else False

        return paginatedPost(
            page = current_page,
            per_page = per_page,
            total = total, 
            total_pages = total_pages,
            has_prev = has_prev,
            has_next = has_next,
            order_by = order_by,
            direction = direction,
            search = query,
            items = items
          
        )

@app.get("/posts/by-tags", response_model=List[PostPublic])
def filter_by_tags(
    tags: list[str]= Query(
        ...,
        min_length=2,
        description="una o mas etiquetas. ejem. ?tags=python&tags=fastapi"

    )
):
    tags_lower = [tag.lower() for tag in tags]
    return[
        post for post in BLOG_POST if any(tag["name"].lower() in tags_lower for tag in post.get("tags",[]))
    ]
    

@app.get("/posts/{post_id}",response_model = Union[PostPublic, PostSummary], response_description="post encontrado")
def get_post(post_id: int = Path(
    ...,
    ge=1,
    title="id del post",
    description= "identificador entero del post. debe sccv             r mayor a 1 ",
    examples=1
), include_content: bool | None = Query(default=True,scription = "buscar titulo"), db: Session=Depends(get_db)):
    post_find = select(PostORM).where(PostORM.id == post_id)
    post = db.execute(post_find).scalar_one_or_none()
    post = db.get(PostORM, post_id)

    if not post:
        raise HTTPException(status_code = 404, detail="post no encontrado")
    if include_content:
        return PostPublic.model_validate(post, from_attributes=True)
    
    return PostSummary.model_validate(post, from_attributes=True)

@app.post("/posts", response_model =PostPublic, response_description="post creado ok ", status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    
    author_obj = None
    if post.author:
        author_obj = db.execute(
            select(AutorORM).where(AutorORM.email == post.author.email)
        ).scalar_one_or_none()


    if not author_obj:
        author_obj = AutorORM(
                              name=post.author.name,
                              email=post.author.email)
        
        db.add(author_obj)
        db.flush()


    new_post = PostORM(title=post.title, content=post.content, author=author_obj)
    for tag in  post.tags:
        tag_obj = db.execute(
            select(TagORM).where(TagORM.name.ilike(tag.name))

        ).scalar_one_or_none()
        if not tag_obj:
            tag_obj = TagORM(name=tag.name)
            db.add(tag_obj)
            db.flush()
    try:
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return new_post
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="el titulo ya existe, coloca otro")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="error al crear el post")
  

@app.put("/posts/{post_id}", response_model = PostPublic, response_description="post actualizado ok", response_model_exclude_none=True) 
def update_post(post_id: int, data: PostUpdate, db: Session = Depends(get_db) ): 
    post = db.get(PostORM, post_id)
    
    if not post:
        raise HTTPException(status_code = 404, detail="post no encontrado")
    
    update = data.model_dump(exclude_unset=True)

    for key, value in update.items():
        setattr(post, key, value)

    db.add(post)
    db.commit()
    db.refresh(post)

            
    return post
        

@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, data: PostUpdate, db: Session = Depends(get_db) ):
    
    post = db.get(PostORM, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post no encontrado")
   
    db.delete(post)
    db.commit()
    return

      