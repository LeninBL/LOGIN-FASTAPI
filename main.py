from fastapi import Cookie
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
import os
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey



# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configuración de seguridad
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
DATABASE_URL = os.getenv("DATABASE_URL")


app = FastAPI()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://login-fastapi-9b3b.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de la base de datos
engine = create_engine(
    DATABASE_URL,
    pool_size=20,       # Aumenta el tamaño del pool
    max_overflow=20,    # Permite más conexiones adicionales
    pool_timeout=1800,    # Tiempo de espera antes de lanzar TimeoutError
    pool_recycle=1800   # Recicla conexiones cada 30 minutos para evitar problemas
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelo de usuario en la base de datos
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)


# Crear todas las tablas en la base de datos
Base.metadata.create_all(bind=engine)




class User(BaseModel):
    username: str
    hashed_password: str


class UserUpdate(BaseModel):
    username: str  
    current_password: str
    new_password: Optional[str] = None
    confirm_password: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

# Función para verificar la contraseña
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Función para obtener un usuario desde la base de datos
def get_user(db, username: str):
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user:
        return User(username=user.username, hashed_password=user.hashed_password)
    return None

# Función para autenticar al usuario
def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# Función para obtener los detalles del usuario
def get_user_details(db, user_id: int):
    return db.query(UserDB).filter(UserDB.user_id == user_id).first()

# Función para crear el token de acceso
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=5)):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({
        "exp": expire,
        "last_activity": datetime.now(timezone.utc).isoformat()
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Verificar si la sesión está expirada por inactividad
def is_session_expired(last_activity: str, inactivity_limit_minutes: int = 1):
    last_activity_time = datetime.fromisoformat(last_activity)
    now = datetime.now(timezone.utc)
    inactivity_duration = now - last_activity_time
    return inactivity_duration > timedelta(minutes=inactivity_limit_minutes)

def token_expired(token: str) -> bool:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp is None:
            return True
        if datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):

            return True
        return False
    except JWTError:
        return True


@app.middleware("http")
async def check_token_expiry(request: Request, call_next):
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                response = RedirectResponse("/", status_code=302)
                response.delete_cookie("access_token")
                response.set_cookie(
                    key="session_expired",
                    value="true",
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                    max_age=3
                )
                return response
        except JWTError:
            response = RedirectResponse("/", status_code=302)
            response.delete_cookie("access_token")
            return response

    response = await call_next(request)
    return response




# Ruta para login
@app.post("/token", response_model=Token)
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    response.set_cookie(
        key="access_token",
        value=access_token,  
        httponly=True,
        secure=True,  
        samesite="Lax"
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Ruta de inicio
@app.get("/")
async def read_root(request: Request):
    token = request.cookies.get("access_token")
    session_expired = False  

    if token:
        return RedirectResponse("/users/me")

    session_expired = request.cookies.get("session_expired", "false") == "true"

    response = templates.TemplateResponse("index.html", {
        "request": request,
        "session_expired": session_expired
    })
    
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/verify-token")
async def verify_token(response: Response, access_token: Optional[str] = Cookie(None)):
    if not access_token or token_expired(access_token):
        response.delete_cookie(key="access_token")
        response.set_cookie(
            key="session_expired",
            value="true",
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=3
        )
        raise HTTPException(status_code=401, detail="Token expirado")
    return {"status": "active"}


# Rutas protegidas
@app.get("/users/me")
async def read_users_me(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        return RedirectResponse("/", status_code=302)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        last_activity = payload.get("last_activity")


        if not last_activity or is_session_expired(last_activity):
            response = RedirectResponse("/", status_code=302)
            response.delete_cookie(key="access_token")  
            

            expires_in=datetime.now(timezone.utc) + timedelta(seconds=3) 

            response.set_cookie(
                key="session_expired",
                value="true",
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=3, 
                expires=expires_in  
            )
            return response
        db = SessionLocal()
        user = get_user(db, username)


        # Actualizar el timestamp de la última actividad
        payload['last_activity'] = datetime.now(timezone.utc).isoformat()
        new_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        response = templates.TemplateResponse("welcome.html", {"request": request, "username": user.username})
        response.set_cookie(
            key="access_token",
            value=new_token,
            httponly=True,
            secure=True,
            samesite="Lax"
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except JWTError:
        return RedirectResponse("/", status_code=302)


@app.get("/users/me/show")
async def read_users_me(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        return RedirectResponse("/", status_code=302)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        last_activity = payload.get("last_activity")

        if not last_activity or is_session_expired(last_activity):
            response = RedirectResponse("/", status_code=302)
            response.delete_cookie(key="access_token")

            expires_in = datetime.now(timezone.utc) + timedelta(seconds=3)
            response.set_cookie(
                key="session_expired",
                value="true",
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=3,
                expires=expires_in
            )
            return response

        db = SessionLocal()
        all_users = db.query(UserDB).all()  # Obtener todos los usuarios

        # Refrescar el token con nueva marca de tiempo
        payload['last_activity'] = datetime.now(timezone.utc).isoformat()
        new_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        response = templates.TemplateResponse("show.html", {
            "request": request,
            "username": username,
            "users": all_users
        })

        response.set_cookie(
            key="access_token",
            value=new_token,
            httponly=True,
            secure=True,
            samesite="Lax"
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except JWTError:
        return RedirectResponse("/", status_code=302)


@app.get("/users/me/register_show")
async def read_users_me_register_show(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        return RedirectResponse("/", status_code=302)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        last_activity = payload.get("last_activity")

        if not last_activity or is_session_expired(last_activity):
            response = RedirectResponse("/", status_code=302)
            response.delete_cookie(key="access_token")

            expires_in = datetime.now(timezone.utc) + timedelta(seconds=3)
            response.set_cookie(
                key="session_expired",
                value="true",
                httponly=True,
                secure=True,
                samesite="Lax",
                max_age=3,
                expires=expires_in
            )
            return response

        db = SessionLocal()
        all_users = db.query(UserDB).all()

        payload['last_activity'] = datetime.now(timezone.utc).isoformat()
        new_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        response = templates.TemplateResponse("register_show.html", {
            "request": request,
            "username": username,
            "users": all_users
        })

        response.set_cookie(
            key="access_token",
            value=new_token,
            httponly=True,
            secure=True,
            samesite="Lax"
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except JWTError:
        return RedirectResponse("/", status_code=302)


@app.post("/users/me/create")
def create_user(user: User, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")

    if not token or token_expired(token):
        raise HTTPException(status_code=401, detail="Token expirado")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        last_activity = payload.get("last_activity")
        if not last_activity or is_session_expired(last_activity):
            raise HTTPException(status_code=401, detail="Sesión expirada")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Validación pasada, ahora sigue la creación de usuario
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario ya existe")

    hashed_password = pwd_context.hash(user.hashed_password)
    new_user = UserDB(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Usuario creado exitosamente"}



# Ruta para logout
@app.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return RedirectResponse("/", status_code=302, headers={
        "Set-Cookie": "access_token=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax"
        
    })

app.mount("/assets", StaticFiles(directory="assets"), name="assets")