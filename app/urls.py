from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    path('', views.index, name='index'),
    path('configuracion/', views.configuracion, name='configuracion'),
    path('api/actualizar-orden/', views.actualizar_orden_obras, name='actualizar_orden_obras'),
    path('eliminar-obra/<int:obra_id>/', views.eliminar_obra, name='eliminar_obra'),
]