from django.contrib import admin
from .models import Beneficiary, Appointment, OrientationRecord

admin.site.register(Beneficiary)
admin.site.register(Appointment)
admin.site.register(OrientationRecord)