from __future__ import annotations

import pandas as pd
import os

class ProductService:
    def __init__(self):
        self.file_path = "static/templates/PARA ENVIAR.xls"
        self.products = []
        self.load_products()

    def load_products(self):
        if not os.path.exists(self.file_path):
            print(f"⚠️ Archivo {self.file_path} no encontrado.")
            return
        try:
            # Según tu nueva descripción, los encabezados están en las primeras filas.
            # Vamos a leer el archivo y forzar que la fila 4 sea el encabezado real 
            # (que en Python es el índice 3), ya que ahí es donde termina tu descripción vertical.
            df = pd.read_excel(self.file_path, header=3) 
            
            # Limpiamos los nombres de las columnas
            df.columns = [str(c).strip() for c in df.columns]
            
            # Reemplazamos los valores nulos para que no den error
            df = df.fillna('')

            # Verificamos que la columna 'Producto' exista tras el ajuste
            if 'Producto' in df.columns:
                self.products = df.to_dict('records')
                print(f"✅ {len(self.products)} productos cargados correctamente desde la nueva estructura.")
            else:
                print(f"❌ Columnas detectadas: {df.columns.tolist()}")
        except Exception as e:
            print(f"❌ Error al cargar Excel: {e}")

    def search_products(self, query: str):
        query = query.lower()
        return [
            {
                "nombre": str(p.get('Producto', '')),
                "unidad": str(p.get('Unidad Medida', 'UND')),
                "codigo": str(p.get('Codigo', 'S/C'))
            }
            for p in self.products 
            if query in str(p.get('Producto', '')).lower()
        ][:20]