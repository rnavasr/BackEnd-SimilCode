from django.db import models

# Create your models here.
class DatosPersonales(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'datos_personales'


class Roles(models.Model):
    nombre = models.CharField(unique=True, max_length=50)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'roles'


class Usuarios(models.Model):
    usuario = models.CharField(unique=True, max_length=50)
    contrasenia = models.CharField(max_length=255)
    datos_personales = models.ForeignKey(DatosPersonales, models.DO_NOTHING)
    rol = models.ForeignKey(Roles, models.DO_NOTHING)
    activo = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usuarios'
