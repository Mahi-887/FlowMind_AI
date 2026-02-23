from django.contrib import admin
from .models import CustomUser, OTPSession, DiagramHistory


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'name', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('phone_number', 'name')
    ordering = ('-date_joined',)


@admin.register(OTPSession)
class OTPSessionAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'otp', 'created_at')
    ordering = ('-created_at',)


@admin.register(DiagramHistory)
class DiagramHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'diagram_type', 'prompt_short', 'created_at')
    list_filter = ('diagram_type',)
    search_fields = ('prompt', 'user__phone_number')
    ordering = ('-created_at',)

    def prompt_short(self, obj):
        return obj.prompt[:60] + '...' if len(obj.prompt) > 60 else obj.prompt
    prompt_short.short_description = 'Prompt'
