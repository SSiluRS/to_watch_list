from pydantic import BaseModel, Field
from typing import Optional, List

class RegisterIn(BaseModel):
    """Данные, передаваемые при регистрации нового пользователя.
    Используется в эндпоинте POST /register.
    """
    username: str = Field(min_length=3, max_length=64, description="Имя пользователя, от 3 до 64 символов.")
    password: str = Field(min_length=4, max_length=128, description="Пароль, от 4 до 128 символов.")

class LoginIn(BaseModel):
    """Данные для авторизации пользователя.
    Используется в эндпоинте POST /login.
    """
    username: str
    password: str

class ListCreate(BaseModel):
    """Данные для создания нового списка.
    Используется в эндпоинте POST /lists.
    """
    name: str

class ItemCreate(BaseModel):
    """Данные для добавления нового элемента в список.
    Используется в эндпоинте POST /items.
    """
    list_id: int
    title: str
    type: str
    cover_url: Optional[str] = ""
    genre: Optional[str] = None

class ItemPatch(BaseModel):
    """Данные для обновления элемента списка.
    Используется в эндпоинте PATCH /items.
    Можно передавать только изменяемые поля.
    """
    id: int
    title: Optional[str] = None
    type: Optional[str] = None
    cover_url: Optional[str] = None
    watched: Optional[bool] = None

class ShareIn(BaseModel):
    """Данные для расшаривания списка другому пользователю.
    Используется в эндпоинте POST /share.
    """
    list_id: int
    username: str

class RenameListIn(BaseModel):
    """Данные для переименования списка.
    Используется в эндпоинте PATCH /rename_list.
    """
    list_id: int
    new_name: str
