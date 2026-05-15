<<<<<<< HEAD
import pandas as pd
from app.models.almacen_articulos import TipoArticulo
from app.repositories.almacen_articulo_repository import AlmacenArticuloRepository
from sqlalchemy.orm import Session
=======
import uuid
import pandas as pd
from sqlalchemy.orm import Session, joinedload
from app.models.almacen_articulos import AlmacenArticulo, TipoArticulo
from app.repositories.almacen_articulo_repository import AlmacenArticuloRepository
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a

class AlmacenArticuloService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AlmacenArticuloRepository(db)

<<<<<<< HEAD
    # --- INVENTARIO (Ahora síncrono para cumplir S7503) ---
    def procesar_inventario_excel(self, file):
        df = pd.read_excel(file.file, skiprows=3)
        df.columns = df.columns.str.strip()
        
        herramientas = [
            'ROTOMARTILLO', 'TALADRO', 'AMOLADORA', 'ESMERIL', 'MOTOSIERRA', 
            'ARNES', 'BOMBA', 'SOLDAR', 'MAQUINA', 'EQUIPO', 'MARTILLO', 
            'CINCEL', 'APLICADOR', 'LLAVE'
        ]
        
        for _, row in df.iterrows():
            if pd.isna(row['Producto']) or pd.isna(row['Codigo']):
                continue
            
            nombre_prod = str(row['Producto']).upper()
            es_equipo = any(h in nombre_prod for h in herramientas)
            
=======
    # --- INVENTARIO ---
    async def procesar_inventario_excel(self, file):
        df = pd.read_excel(file.file, skiprows=3)
        df.columns = df.columns.str.strip()
        for _, row in df.iterrows():
            if pd.isna(row['Producto']) or pd.isna(row['Codigo']):
                continue
            nombre_prod = str(row['Producto']).upper()
            herramientas = ['ROTOMARTILLO', 'TALADRO', 'AMOLADORA', 'ESMERIL', 'MOTOSIERRA', 'ARNES', 'BOMBA', 'SOLDAR','MAQUINA','EQUIPO','MARTILLO','CINCEL','APLICADOR','LLAVE']
            es_equipo = any(h in nombre_prod for h in herramientas)
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
            self.repo.upsert_articulo({
                "nombre": row['Producto'],
                "unidad_medida": row['Unidad Medida'],
                "tipo": TipoArticulo.EQUIPO if es_equipo else TipoArticulo.CONSUMIBLE,
                "stock_actual": 5,
                "codigo_excel": str(row['Codigo'])
            })
        return len(df)
<<<<<<< HEAD

    def buscar_articulos(self, termino: str):
        if len(termino) < 2:
            return self.repo.get_all_disponibles()
        return self.repo.search_articulos(termino)
=======
    def buscar_articulos(self, termino: str):
        if len(termino) < 2:  # Opcional: no buscar si solo hay 1 letra
            return self.repo.get_all_disponibles()
        return self.repo.search_articulos(termino)
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
