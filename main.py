from fastapi import *
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import async_session, AsyncSession
from jose import JWTError, jwt
from sqlalchemy.orm import selectinload

import utils
from models import schemas, models
from models.models import *
from sqlalchemy.future import select

from films import *

import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.post("/register/", response_model=schemas.UserBase)
async def register_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    query = select(models.User).where(models.User.username == user.username)
    result = await db.execute(query)
    db_user = result.scalars().first()

    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered!")

    hashed_password = await utils.get_password_hash(user.password)
    new_user = models.User(username=user.username, password=hashed_password)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@app.post("/login/")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    query = select(models.User).where(models.User.username == form_data.username)
    result = await db.execute(query)
    user = result.scalars().first()

    if not user or not await utils.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Beaver"}
        )

    access_token = await utils.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication")

        query = select(models.User).options(selectinload(models.User.stars)).where(models.User.username == username)
        result = await db.execute(query)
        user = result.scalars().first()

        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
        return user
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/profile/", response_model=schemas.UserResponse)
async def read_profile(current_user: schemas.UserResponse = Depends(get_current_user)):
    return current_user


@app.get("/movies/search")
async def search_movie(query: str, cur_user: schemas.UserResponse = Depends(get_current_user)):
    external_api_url = "https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword"
    params = {"keyword": query}
    headers = {"X-API-KEY": os.getenv("KINOPOISK_TOKEN"), "Content-Type": "application/json"}

    film_obj = FilmAPI(external_api_url, headers, params)
    data = await film_obj.fetch_data()

    movies = [
        {
            "film_id": movie["filmId"],
            "rating": movie["rating"],
            "year": movie["year"],
            "countries": movie['countries'],
            "poster_url": movie['posterUrl'],
        }
        for movie in data.get("films", [])
    ]
    return movies


@app.get("/movies/")
async def search_movie_details(id: int, cur_user: schemas.UserResponse = Depends(get_current_user)):
    external_api_url = f"https://kinopoiskapiunofficial.tech//api/v2.2/films/{id}"
    headers = {"X-API-KEY": os.getenv("KINOPOISK_TOKEN"), "Content-Type": "application/json"}
    film_obj = FilmAPI(external_api_url, headers)
    data = await film_obj.fetch_data()
    return data


@app.post("/movies/favorites", response_model=schemas.MovieInFavoritesResponse)
async def add_movie_to_favorites(favorite_data: schemas.MovieFavoriteRequest,
                                 db: AsyncSession = Depends(get_db),
                                 cur_user: models.User = Depends(get_current_user)):
    query = select(models.StarredFilm).where(models.StarredFilm.film_id == favorite_data.film_id)
    result = await db.execute(query)
    movie = result.scalars().first()

    if not movie:
        movie = models.StarredFilm(
            film_id=favorite_data.film_id,
            film_name=favorite_data.film_name,
            year=favorite_data.year,
            imdb_id=favorite_data.imdb_id,
            film_length=favorite_data.film_length,
            film_poster=favorite_data.film_poster,
            film_link=favorite_data.film_link
        )
        db.add(movie)
        await db.commit()
        await db.refresh(movie)

    if movie not in cur_user.stars:
        cur_user.stars.append(movie)

        try:
            await db.commit()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add movie to favorites: " + str(e)
            )

    return {"message": "Movie added to favorites", "movie": movie}


@app.delete("/movies/favorites/{kinopoisk_id}", response_model=schemas.MovieRemovedResponse)
async def remove_fav_film(kinopoisk_id: int,
                          db: AsyncSession = Depends(get_db),
                          cur_user: models.User = Depends(get_current_user)):
    query = select(models.StarredFilm).where(models.StarredFilm.film_id == kinopoisk_id)
    result = await db.execute(query)
    movie = result.scalars().first()

    if not movie or movie not in cur_user.stars:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Movie not found in your favorites")
    cur_user.stars.remove(movie)
    await db.commit()

    return {"message": "Movie removed from favorites", "movie_id": kinopoisk_id}
