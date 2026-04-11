"""Update foto_url in DB to use local paths."""
import json
import urllib.request
from db import get_db
from models.imovel import Imovel

db = next(get_db())
imoveis = db.query(Imovel).all()

updated = 0
for imovel in imoveis:
    new_url = f"/imoveis/imovel-{imovel.id}.jpg"
    if imovel.foto_url != new_url:
        imovel.foto_url = new_url
        updated += 1

db.commit()
print(f"Atualizados: {updated} imóveis")
