import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '10s', target: 20 },  // Sube a 20 usuarios
        { duration: '20s', target: 50 },  // Sube a 50 usuarios
        { duration: '20s', target: 300 }, // Sube a 100 usuarios (Punto de quiebre)
        { duration: '10s', target: 0 },   // Baja a 0
    ],
};

export default function () {
    const url = 'http://localhost:8000/almacen/registrar-prestamo-qr';
    
    // Datos basados en tu PrestamoQRData Schema
    const payload = JSON.stringify({
        trabajador_id: 1,
        codigo_unico: "REQ-101",
        dni: "12345678",
        nombres_completos: "Juan Perez",
        cargo: "Operario",
        fecha_prestamo: "2026-04-30T10:00:00",
        fecha_devolucion_prevista: "2026-05-01T10:00:00",
        items: [
            { articulo_id: 1, cantidad: 2 }
        ],
        firma_base64: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..." 
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer TU_TOKEN_AQUI',
        },
    };

    let res = http.post(url, payload, params);

    check(res, {
        'prestamo creado o error validacion': (r) => r.status === 200 || r.status === 400,
        'no hay error 500': (r) => r.status !== 500,
    });

    sleep(1);
}