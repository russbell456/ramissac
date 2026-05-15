import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    vus: 5,           // Solo 5 usuarios para verificar estabilidad
    duration: '10s', 
};

export default function () {
    const params = {
        headers: {
            'Authorization': 'Bearer TU_TOKEN_AQUI', // Reemplaza con un token válido
        },
    };

    // Probamos el catálogo de artículos
    let res = http.get('http://localhost:8000/articulo/articulos', params);
    
    check(res, {
        'status es 200': (r) => r.status === 200,
        'devuelve lista': (r) => Array.isArray(r.json()),
    });

    sleep(1);
}