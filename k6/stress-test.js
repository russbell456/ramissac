import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
<<<<<<< HEAD
        { duration: '10s', target: 20 },  // Sube a 20 usuarios
        { duration: '20s', target: 50 },  // Sube a 50 usuarios
        { duration: '20s', target: 300 }, // Sube a 100 usuarios (Punto de quiebre)
        { duration: '10s', target: 0 },   // Baja a 0
    ],
=======
        { duration: '15s', target: 30 },  // Subida suave a 30 usuarios
        { duration: '30s', target: 100 }, // Carga máxima de 100 usuarios (Sostenible)
        { duration: '15s', target: 0 },   // Bajada controlada
    ],
    thresholds: {
        http_req_failed: ['rate<0.01'],   // El reporte fallará si hay más de 1% de errores
        http_req_duration: ['p(95)<2000'], // El 95% de las peticiones deben durar menos de 2s
    },
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
};

export default function () {
    const url = 'http://localhost:8000/almacen/registrar-prestamo-qr';
    
<<<<<<< HEAD
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
=======
    const payload = JSON.stringify({
        trabajador_id: 1,
        // Usamos una estampa de tiempo para que el código sea siempre único y no choque en la DB
        codigo_unico: `REQ-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
        dni: "12345678",
        nombres_completos: "Prueba de Carga",
        cargo: "Operario",
        fecha_prestamo: new Date().toISOString(),
        fecha_devolucion_prevista: new Date(Date.now() + 86400000).toISOString(),
        items: [
            { articulo_id: 1, cantidad: 1 }
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
        ],
        firma_base64: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..." 
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
<<<<<<< HEAD
            'Authorization': 'Bearer TU_TOKEN_AQUI',
=======
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJsYXVyYUBlbXByZXNhLmNvbSIsInJvbGUiOiJhbG1hY2VuZXJvIiwiZXhwIjoxNzc3NTc0MzY4fQ.Ee5XZhiFISrysM-b82_L0b4zlte_jJdnCXcHmsFYW1c',
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
        },
    };

    let res = http.post(url, payload, params);

    check(res, {
<<<<<<< HEAD
        'prestamo creado o error validacion': (r) => r.status === 200 || r.status === 400,
        'no hay error 500': (r) => r.status !== 500,
    });

    sleep(1);
=======
        'autorización correcta': (r) => r.status !== 401 && r.status !== 403,
        'registro procesado (200 o 400)': (r) => r.status === 200 || r.status === 400,
        'sin errores de servidor (500)': (r) => r.status !== 500,
    });

    // Aumentamos el sleep a 1.5s para darle un respiro a la base de datos entre peticiones
    sleep(1.5);
>>>>>>> e11366450dc900be412f7c6cfe72ffffb0b3c07a
}