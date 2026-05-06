import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    vus: 20, 
    duration: '30s',
};

export default function () {
    const url = 'http://localhost:8000/articulo/buscar?q=martillo'; // Cambia 'martillo' por algo que exista en tu DB
    const params = {
        headers: {
            'Authorization': 'Bearer TU_TOKEN_AQUI',
        },
    };

    let res = http.get(url, params);

    check(res, {
        'busqueda exitosa (200)': (r) => r.status === 200,
        'tiempo respuesta < 500ms': (r) => r.timings.duration < 500,
    });

    sleep(1);
}