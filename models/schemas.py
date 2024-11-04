from pydantic import BaseModel
from typing import Optional


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int

    class Config:
        orm_mode = True


class MovieFavoriteRequest(BaseModel):
    film_id: int
    film_name: str
    year: int
    imdb_id: int
    film_length: int
    film_poster: str
    film_link: str


class MovieInFavoritesResponse(BaseModel):
    message: str
    movie: MovieFavoriteRequest


class MovieRemovedResponse(BaseModel):
    message: str
    movie_id: int
