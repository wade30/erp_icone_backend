from django.contrib import admin
from .models import Account, Journal, AccountingEntry, EntryLine

admin.site.register(Account)
admin.site.register(Journal)
admin.site.register(AccountingEntry)
admin.site.register(EntryLine)