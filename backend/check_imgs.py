from db import get_db
from models.imovel import Imovel
db = next(get_db())
imgs = [(i.titulo, i.foto_url) for i in db.query(Imovel).limit(10).all()]
for t, u in imgs:
    print(t, "->", u)
