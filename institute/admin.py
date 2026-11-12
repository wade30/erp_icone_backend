from django.contrib import admin
from .models import Course, Learner, Enrollment

admin.site.register(Course)
admin.site.register(Learner)
admin.site.register(Enrollment)