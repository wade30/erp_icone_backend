from django.contrib import admin
from .models import BankAccount, Receipt, ExpenseRequest

admin.site.register(BankAccount)
admin.site.register(Receipt)
admin.site.register(ExpenseRequest)