from django.contrib import admin
from .models import Bahan, Pesanan, ItemPesanan, Siklus, MenuSiklus

# Pendaftaran model yang sudah ada
admin.site.register(Bahan)
admin.site.register(Pesanan)
admin.site.register(ItemPesanan)

# =========================
# INLINE MENU SIKLUS
# =========================
class MenuSiklusInline(admin.TabularInline):
    model = MenuSiklus
    extra = 1  # Jumlah baris kosong default yang disediakan

# =========================
# ADMIN SIKLUS UTAMA
# =========================
class SiklusAdmin(admin.ModelAdmin):
    list_display = ('nama', 'keterangan')
    inlines = [MenuSiklusInline] # Menyatukan inputan detail bahan ke dalam form siklus

# Mendaftarkan model Siklus dengan tampilan admin khusus
admin.site.register(Siklus, SiklusAdmin)