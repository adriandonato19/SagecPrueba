const fetch = require('node-fetch'); // O nativo en Node 18+

async function consultarAPI() {
    try {
        // Hacemos la petición a la API
        const response = await fetch('https://jsonplaceholder.typicode.com/todos/1');
        
        // Verificamos si la respuesta es correcta
        if (!response.ok) {
            throw new Error(`Error HTTP: ${response.status}`);
        }

        // Convertimos la respuesta a JSON
        const data = await response.json();
        
        // Mostramos los datos
        console.log('Datos recibidos:', data);
    } catch (error) {
        console.error('Hubo un error al consultar la API:', error);
    }
}

consultarAPI();
