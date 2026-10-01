from app.database.connection import engine
from sqlalchemy import text

def patch():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE jornadas_transporte ADD COLUMN accion_tipo VARCHAR"))
            print("Added accion_tipo")
        except Exception as e:
            print("accion_tipo:", e)
        try:
            conn.execute(text("ALTER TABLE jornadas_transporte ADD COLUMN ruta VARCHAR"))
            print("Added ruta")
        except Exception as e:
            print("ruta:", e)
        try:
            conn.execute(text("ALTER TABLE jornadas_transporte ADD COLUMN nivel_combustible INTEGER"))
            print("Added nivel_combustible")
        except Exception as e:
            print("nivel_combustible:", e)
        try:
            conn.execute(text("ALTER TABLE jornadas_transporte ADD COLUMN checklist_flash JSON"))
            print("Added checklist_flash")
        except Exception as e:
            print("checklist_flash:", e)
        try:
            conn.execute(text("ALTER TABLE jornadas_transporte ADD COLUMN observaciones TEXT"))
            print("Added observaciones")
        except Exception as e:
            print("observaciones:", e)
        conn.commit()
    print("Patch completado")

if __name__ == "__main__":
    patch()
