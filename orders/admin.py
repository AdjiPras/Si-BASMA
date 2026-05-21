from django.contrib import admin
from .models import Bahan, Pesanan, ItemPesanan

admin.site.register(Bahan)
admin.site.register(Pesanan)
admin.site.register(ItemPesanan)