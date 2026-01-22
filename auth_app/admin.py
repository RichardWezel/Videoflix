from django.contrib import admin
from .models import CustomUser

@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):

    list_display = ('id', 'email', 'is_active', 'is_staff', 'is_superuser', 'account_activated')
    search_fields = ('email',)
    ordering = ('-id',)