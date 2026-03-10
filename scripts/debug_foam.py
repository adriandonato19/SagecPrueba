import os
import django
import sys
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from tramites.views import crear_tramite_view
from integracion.services import buscar_empresa
from django.contrib.auth import get_user_model
User = get_user_model()

def debug_foam():
    print(">>> 1. Buscando 'FOAM CLEAN SERVICE'")
    resultado = buscar_empresa("FOAM CLEAN SERVICE")
    
    if not resultado:
        print("[ERROR] No se encontraron resultados para FOAM CLEAN SERVICE")
        return
        
    print(f"[OK] Encontrados {len(resultado['avisos'])} avisos.")
    # Imprimir detalles para verificar
    for a in resultado['avisos']:
        print(f"   - {a.get('razon_social')} | RUC: {a.get('ruc')} | Aviso: {a.get('numero_aviso')}")
        
    # Simular selección del primer aviso
    seleccionado = resultado['avisos'][0]
    aviso_id = seleccionado.get('numero_aviso')
    ruc_sel = seleccionado.get('ruc')
    
    print(f"\n>>> 2. Simulando Creación de Trámite para Aviso ID: {aviso_id}")
    
    factory = RequestFactory()
    
    # GET Request simulación
    request_get = factory.get(f'/tramites/crear/?crear_tramite={ruc_sel}&aviso={aviso_id}')
    
    # Setup middleware (session, messages, user)
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request_get)
    request_get.session.save()
    
    # INYECTAR RESULTADOS EN SESIÓN (Como hace la vista de búsqueda)
    request_get.session['avisos_busqueda'] = resultado['avisos']
    request_get.session.save()
    
    # Mock user
    user = User.objects.first() or User.objects.create(username='test_user')
    request_get.user = user
    message_middleware = MessageMiddleware(lambda x: None)
    message_middleware.process_request(request_get)
    
    # Ejecutar Vista GET
    print(">>> Ejecutando Vista GET...")
    response_get = crear_tramite_view(request_get)
    print(f"[GET] Status Code: {response_get.status_code}")
    
    # Verificar Contexto (si es render)
    # Nota: response_get es HttpResponse, no tiene context directo fácil de leer sin renderizar, 
    # pero podemos interceptar log_debug en consola si configuramos.
    # O ver el contenido HTML en busca de valores.
    content = response_get.content.decode('utf-8')
    if seleccionado['razon_social'] in content:
        print(f"[OK] Razón social '{seleccionado['razon_social']}' encontrada en HTML.")
    else:
        print(f"[FAIL] Razón social NO encontrada en HTML.")
        
    # POST Request simulación
    print("\n>>> 3. Simulando POST (Crear)...")
    data = {
        'ruc': ruc_sel,
        'tipo_documento': 'CERTIFICADO',
        'destinatario': 'TEST USER',
        'proposito': 'TEST DEBUG',
        'aviso': aviso_id
    }
    request_post = factory.post('/tramites/crear/', data)
    middleware.process_request(request_post)
    request_post.session['avisos_busqueda'] = resultado['avisos'] # Persistir sesión
    request_post.session.save()
    request_post.user = user
    message_middleware.process_request(request_post)
    
    try:
        response_post = crear_tramite_view(request_post)
        print(f"[POST] Status Code: {response_post.status_code}")
        if response_post.status_code == 302:
            print("[OK] Redirección exitosa (Trámite creado).")
        else:
            print("[FAIL] No redirigió.")
    except Exception as e:
        print(f"[CRASH] {e}")

if __name__ == "__main__":
    debug_foam()
