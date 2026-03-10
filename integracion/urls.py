from django.urls import path
from . import views

app_name = 'integracion'

urlpatterns = [
    path('consultar/', views.buscador_view, name='buscador'),
    path('hx/buscar-empresa/', views.api_search_view, name='api_search'),
    path('hx/detalle-empresa/<str:aviso>/', views.detalle_empresa_hx, name='detalle_empresa_hx'),
    path('hx/carrito/agregar/<str:aviso>/', views.agregar_al_carrito_hx, name='agregar_carrito'),
    path('hx/carrito/remover/<str:aviso>/', views.remover_del_carrito_hx, name='remover_carrito'),
    path('hx/carrito/status/', views.status_carrito_hx, name='status_carrito'),
]
