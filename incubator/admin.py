from django.contrib import admin
from .models import Entrepreneur, Project, CoachingSession

admin.site.register(Entrepreneur)
admin.site.register(Project)
admin.site.register(CoachingSession)